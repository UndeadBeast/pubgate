import asyncio

from sanic import response, Blueprint
from sanic_openapi import doc

from pubgate.api.v1.db.models import User, Outbox
from pubgate.api.v1.renders import context, Activity
from pubgate.api.v1.utils import make_label, _to_list
from pubgate.api.v1.networking import deliver
from pubgate.api.v1.views.auth import auth_required

outbox_v1 = Blueprint('outbox_v1')


@outbox_v1.route('/<user_id>', methods=['POST'])
@doc.summary("Post to user outbox, auth required")
@doc.consumes(Outbox, location="body")
@auth_required
async def outbox_post(request, user_id):
    # TODO handle replies
    user = await User.find_one(dict(username=user_id))
    if not user:
        return response.json({"zrada": "no such user"}, status=404)

    # TODO validate activity
    activity = Activity(request.app.v1_path, user_id, request.json)
    await Outbox.insert_one({
            "_id": activity.obj_id,
            "user_id": user_id,
            "activity": activity.render,
            "label": make_label(activity.render),
            "meta": {"undo": False, "deleted": False},
         })

    if activity.render["type"] == "Follow":
        recipients = [activity.render["object"]]
    else:
        recipients = await user.followers_get()
        for field in ["to", "cc", "bto", "bcc"]:
            if field in activity.render:
                recipients.extend(_to_list(activity.render[field]))
        recipients = list(set(recipients))

    # post_to_remote_inbox
    asyncio.ensure_future(deliver(activity.render, recipients))

    return response.json({'peremoga': 'yep'})


@outbox_v1.route('/<user_id>', methods=['GET'])
@doc.summary("Returns user outbox")
async def outbox_list(request, user_id):
    user = await User.find_one(dict(username=user_id))
    if not user:
        return response.json({"zrada": "no such user"}, status=404)
    resp = await user.outbox_paged(request)
    return response.json(resp, headers={'Content-Type': 'application/activity+json; charset=utf-8'})


@outbox_v1.route('/<user_id>/<activity_id>', methods=['GET'])
@doc.summary("Returns item from outbox")
async def outbox_item(request, user_id, activity_id):
    user = await User.find_one(dict(username=user_id))
    if not user:
        return response.json({"zrada": "no such user"}, status=404)

    data = await Outbox.find_one(dict(user_id=user_id, _id=activity_id))
    if not data:
        return response.json({"zrada": "no such activity"}, status=404)

    activity = data["activity"]
    activity['@context'] = context

    return response.json(activity, headers={'Content-Type': 'application/activity+json; charset=utf-8'})


@outbox_v1.route('/<user_id>/<activity_id>/activity', methods=['GET'])
@doc.summary("Returns activity from outbox")
async def outbox_activity(request, user_id, activity_id):
    user = await User.find_one(dict(username=user_id))
    if not user:
        return response.json({"zrada": "no such user"}, status=404)

    data = await Outbox.find_one(dict(user_id=user_id, _id=activity_id))
    if not data:
        return response.json({"zrada": "no such activity"}, status=404)

    activity = data["activity"]["object"]
    activity['@context'] = context

    return response.json(activity, headers={'Content-Type': 'application/activity+json; charset=utf-8'})
