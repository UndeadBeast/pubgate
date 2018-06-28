import binascii
import os
import typing

import requests

from little_boxes.__version__ import __version__
from little_boxes.errors import ActivityNotFoundError
from little_boxes.errors import RemoteActivityGoneError
from little_boxes.urlutils import check_url, InvalidURLError
from little_boxes.activitypub import _to_list

from pubgate.db.models import Outbox


if typing.TYPE_CHECKING:
    from little_boxes import activitypub as ap  # noqa: type checking

from pubgate import version
import asyncio


async def fetch(session, url):
    async with session.get(url) as resp:
        return await resp.json()


class NotBackend:

    def fetch_iri(self, iri: str, **kwargs) -> "ap.ObjectType":  # pragma: no cover

        check_url(iri, self.debug)

        # loop = asyncio.get_event_loop()
        # bu = loop.create_task(fetch(self.session, iri))

        # bu = asyncio.ensure_future(fetch(self.client_session, iri), loop=loop)


        # async def slow_operation(future):
        #     await asyncio.sleep(1)
        #     future.set_result('Future is done!')
        #
        # def got_result(future):
        #     print(future.result())
        #
        # # loop = asyncio.get_event_loop()
        # future = asyncio.Future()
        # asyncio.ensure_future(slow_operation(future))
        # x = future.add_done_callback(got_result)



        # responses = loop.run_until_complete(fetch(self.client_session, iri))
        # print(responses)

        # resp = requests.get(
        #     iri,
        #     headers={
        #         "User-Agent": self.user_agent(),
        #         "Accept": "application/activity+json",
        #     },
        #     **kwargs,
        # )

        # if resp.status_code == 404:
        #     raise ActivityNotFoundError(f"{iri} is not found")
        # elif resp.status_code == 410:
        #     raise RemoteActivityGoneError(f"{iri} is gone")
        #
        # resp.raise_for_status()

        return self.profile

    def activity_url(self, obj_id):
        """URL for activity link."""
        return f"{self.base_url}/api/v1/outbox/{obj_id}"

    def note_url(self, obj_id):
        return self.activity_url(obj_id)

    def debug_mode(self) -> bool:
        """Should be overidded to return `True` in order to enable the debug mode."""
        return self.debug

    def user_agent(self) -> str:
        return (
            f"{requests.utils.default_user_agent()} (Pubgate/{version};"
            " +http://github.com/autogestion/pubgate)"
        )

    def random_object_id(self) -> str:
        """Generates a random object ID."""
        return binascii.hexlify(os.urandom(8)).decode("utf-8")

    def fetch_json(self, url: str, **kwargs):
        check_url(url)
        resp = requests.get(
            url,
            headers={"User-Agent": self.user_agent(), "Accept": "application/json"},
            **kwargs,
        )

        resp.raise_for_status()

        return resp

    def is_from_outbox(
        self, as_actor: "ap.Person", activity: "ap.BaseActivity"
    ) -> bool:
        return activity.get_actor().id == as_actor.id

    def post_to_remote_inbox(self, as_actor, payload: str, to: str) -> None:
        # tasks.post_to_inbox.delay(payload, to)
        pass

    def outbox_create(self, as_actor, create) -> None:
        self._handle_replies(as_actor, create)


async def insert_one(model, paylad):
    await model.insert_one(paylad)


class PGBackend(NotBackend):

    def outbox_new(self, as_actor, activity) -> None:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(insert_one(Outbox,
             {
                "activity": activity.to_dict(),
                "type": _to_list(activity.type),
                "remote_id": activity.id,
                "meta": {"undo": False, "deleted": False},
             }), loop=loop)

    def _handle_replies(self, as_actor, create) -> None:
        """Go up to the root reply, store unknown replies in the `threads` DB and set the "meta.thread_root_parent"
        key to make it easy to query a whole thread."""
        in_reply_to = create.get_object().inReplyTo
        if not in_reply_to:
            return

        # new_threads = []
        # root_reply = in_reply_to
        # reply = ap.fetch_remote_activity(root_reply, expected=ap.ActivityType.NOTE)
        #
        # if not DB.inbox.find_one_and_update(
        #     {"activity.object.id": in_reply_to},
        #     {"$inc": {"meta.count_reply": 1, "meta.count_direct_reply": 1}},
        # ):
        #     if not DB.outbox.find_one_and_update(
        #         {"activity.object.id": in_reply_to},
        #         {"$inc": {"meta.count_reply": 1, "meta.count_direct_reply": 1}},
        #     ):
        #         # It means the activity is not in the inbox, and not in the outbox, we want to save it
        #         DB.threads.insert_one(
        #             {
        #                 "activity": reply.to_dict(),
        #                 "type": _to_list(reply.type),
        #                 "remote_id": reply.id,
        #                 "meta": {"undo": False, "deleted": False},
        #             }
        #         )
        #         new_threads.append(reply.id)
        #
        # while reply is not None:
        #     in_reply_to = reply.inReplyTo
        #     if not in_reply_to:
        #         break
        #     root_reply = in_reply_to
        #     reply = ap.fetch_remote_activity(root_reply, expected=ap.ActivityType.NOTE)
        #     q = {"activity.object.id": root_reply}
        #     if not DB.inbox.count(q) and not DB.outbox.count(q):
        #         DB.threads.insert_one(
        #             {
        #                 "activity": reply.to_dict(),
        #                 "type": _to_list(reply.type),
        #                 "remote_id": reply.id,
        #                 "meta": {"undo": False, "deleted": False},
        #             }
        #         )
        #         new_threads.append(reply.id)
        #
        # q = {"remote_id": create.id}
        # if not DB.inbox.find_one_and_update(
        #     q, {"$set": {"meta.thread_root_parent": root_reply}}
        # ):
        #     DB.outbox.update_one(q, {"$set": {"meta.thread_root_parent": root_reply}})
        #
        # DB.threads.update(
        #     {"remote_id": {"$in": new_threads}},
        #     {"$set": {"meta.thread_root_parent": root_reply}},
        # )
