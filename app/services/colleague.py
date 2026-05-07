from datetime import datetime, timezone

from sqlalchemy import or_
from sqlmodel import func, select

from app.core.database import SessionDep
from app.models.colleague import Colleague
from app.models.user import User
from app.schemas.colleague import ColleagueRelationStatus


class ColleagueService:
    @staticmethod
    def _get_user_by_username_or_404(username: str, session: SessionDep) -> User:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found")
        return user

    @staticmethod
    def _summarize_user(user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "firstname": user.firstname,
            "lastname": user.lastname,
        }

    @staticmethod
    def _find_relation(user_a_id: int, user_b_id: int, session: SessionDep) -> Colleague | None:
        return session.exec(
            select(Colleague).where(
                or_(
                    (Colleague.from_user_id == user_a_id) & (Colleague.to_user_id == user_b_id),
                    (Colleague.from_user_id == user_b_id) & (Colleague.to_user_id == user_a_id),
                )
            )
        ).first()

    @staticmethod
    def get_relation_status(current_user_id: int, target_username: str, session: SessionDep) -> ColleagueRelationStatus:
        target = ColleagueService._get_user_by_username_or_404(target_username, session)
        if target.id == current_user_id:
            return "self"

        relation = ColleagueService._find_relation(current_user_id, target.id, session)
        if not relation:
            return "none"
        if relation.status == "accepted":
            return "accepted"
        if relation.from_user_id == current_user_id:
            return "pending_outgoing"
        return "pending_incoming"

    @staticmethod
    def count_colleagues(user_id: int, session: SessionDep) -> int:
        return int(
            session.exec(
                select(func.count(Colleague.id)).where(
                    Colleague.status == "accepted",
                    or_(
                        Colleague.from_user_id == user_id,
                        Colleague.to_user_id == user_id,
                    ),
                )
            ).one()
            or 0
        )

    @staticmethod
    def send_or_accept(current_user_id: int, target_username: str, session: SessionDep) -> tuple[str, dict, str]:
        target = ColleagueService._get_user_by_username_or_404(target_username, session)
        if target.id == current_user_id:
            raise ValueError("You cannot add yourself as a colleague")

        relation = ColleagueService._find_relation(current_user_id, target.id, session)
        if relation:
            if relation.status == "accepted":
                return "accepted", ColleagueService._summarize_user(target), "Already colleagues."
            if relation.from_user_id == current_user_id:
                return "pending", ColleagueService._summarize_user(target), "Request already sent."

            relation.status = "accepted"
            relation.accepted_at = datetime.now(timezone.utc)
            session.add(relation)
            session.commit()
            return "accepted", ColleagueService._summarize_user(target), "Colleague request accepted."

        created = Colleague(
            from_user_id=current_user_id,
            to_user_id=target.id,
            status="pending",
        )
        session.add(created)
        session.commit()
        return "pending", ColleagueService._summarize_user(target), "Colleague request sent."

    @staticmethod
    def accept_request(current_user_id: int, from_username: str, session: SessionDep) -> tuple[str, dict, str]:
        sender = ColleagueService._get_user_by_username_or_404(from_username, session)
        if sender.id == current_user_id:
            raise ValueError("You cannot accept your own request")

        relation = session.exec(
            select(Colleague).where(
                Colleague.from_user_id == sender.id,
                Colleague.to_user_id == current_user_id,
            )
        ).first()

        if not relation:
            raise ValueError("No colleague request from this user")

        if relation.status == "accepted":
            return "accepted", ColleagueService._summarize_user(sender), "Already colleagues."

        relation.status = "accepted"
        relation.accepted_at = datetime.now(timezone.utc)
        session.add(relation)
        session.commit()
        return "accepted", ColleagueService._summarize_user(sender), "Colleague request accepted."

    @staticmethod
    def remove_relation(current_user_id: int, target_username: str, session: SessionDep) -> tuple[str, dict, str]:
        target = ColleagueService._get_user_by_username_or_404(target_username, session)
        if target.id == current_user_id:
            raise ValueError("You cannot remove yourself")

        relation = ColleagueService._find_relation(current_user_id, target.id, session)
        if relation:
            session.delete(relation)
            session.commit()

        return "removed", ColleagueService._summarize_user(target), "Colleague relation removed."

    @staticmethod
    def list_for_user(current_user_id: int, session: SessionDep) -> dict:
        rows = session.exec(
            select(Colleague).where(
                or_(
                    Colleague.from_user_id == current_user_id,
                    Colleague.to_user_id == current_user_id,
                )
            )
        ).all()

        other_ids = {
            row.to_user_id if row.from_user_id == current_user_id else row.from_user_id
            for row in rows
        }
        users = session.exec(select(User).where(User.id.in_(other_ids))).all() if other_ids else []
        user_map = {u.id: u for u in users}

        colleagues: list[dict] = []
        outgoing_pending: list[dict] = []
        incoming_pending: list[dict] = []

        for row in rows:
            other_id = row.to_user_id if row.from_user_id == current_user_id else row.from_user_id
            other = user_map.get(other_id)
            if not other:
                continue
            summary = ColleagueService._summarize_user(other)
            if row.status == "accepted":
                colleagues.append(summary)
            elif row.from_user_id == current_user_id:
                outgoing_pending.append(summary)
            else:
                incoming_pending.append(summary)

        colleagues.sort(key=lambda item: item["username"].lower())
        outgoing_pending.sort(key=lambda item: item["username"].lower())
        incoming_pending.sort(key=lambda item: item["username"].lower())

        return {
            "colleagues": colleagues,
            "outgoing_pending": outgoing_pending,
            "incoming_pending": incoming_pending,
            "incoming_count": len(incoming_pending),
        }

    @staticmethod
    def list_public_by_username(username: str, session: SessionDep) -> dict:
        owner = ColleagueService._get_user_by_username_or_404(username, session)
        rows = session.exec(
            select(Colleague).where(
                Colleague.status == "accepted",
                or_(
                    Colleague.from_user_id == owner.id,
                    Colleague.to_user_id == owner.id,
                ),
            )
        ).all()

        other_ids = {
            row.to_user_id if row.from_user_id == owner.id else row.from_user_id
            for row in rows
        }
        users = session.exec(select(User).where(User.id.in_(other_ids))).all() if other_ids else []
        colleagues = [ColleagueService._summarize_user(user) for user in users]
        colleagues.sort(key=lambda item: item["username"].lower())

        return {
            "username": owner.username,
            "colleagues": colleagues,
            "total": len(colleagues),
        }
