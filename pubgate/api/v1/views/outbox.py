from datetime import datetime
import asyncio

from asgiref.sync import sync_to_async
from sanic import response, Blueprint
from sanic_openapi import doc

from little_boxes.activitypub import parse_activity, _to_list
from little_boxes.errors import UnexpectedActivityTypeError, BadActivityError

from pubgate.api.v1.db.models import User, Outbox
from pubgate.api.v1.renders import context
from pubgate.api.v1.utils import make_label, random_object_id, auth_required
from pubgate.api.v1.networking import deliver

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
    # Disabled while issue  https://github.com/tsileo/little-boxes/issues/8 will be fixed
    # try:
    #     activity = await sync_to_async(parse_activity)(request.json)
    # except (UnexpectedActivityTypeError, BadActivityError) as e:
    #     return response.json({"zrada": e})
    activity = request.json.copy()
    obj_id = random_object_id()
    now = datetime.now()

    outbox_url = f"{request.app.v1_path}/outbox/{user_id}"
    activity["id"] = f"{outbox_url}/{obj_id}"
    activity["published"] = now.isoformat()
    if isinstance(activity["object"], dict):
        activity["object"]["id"] = f"{outbox_url}/{obj_id}/activity"
        activity["object"]["published"] = now.isoformat()

    await Outbox.insert_one({
            "_id": obj_id,
            "user_id": user_id,
            "activity": activity,
            "label": make_label(activity),
            "meta": {"undo": False, "deleted": False},
         })

    if activity["type"] == "Follow":
        recipients = [activity["object"]]
    else:
        recipients = await user.followers_get()
        for field in ["to", "cc", "bto", "bcc"]:
            if field in activity:
                recipients.extend(_to_list(activity[field]))
        recipients = list(set(recipients))

    # post_to_remote_inbox
    asyncio.ensure_future(deliver(activity, recipients))

    return response.json({'peremoga': 'yep', 'id': obj_id})


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
