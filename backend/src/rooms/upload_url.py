from shared.http import ok


def handler(event, context):
    # TODO person 3: presigned PUT for key rooms/<code>/<round>/<playerId>.jpg (ContentType image/jpeg).
    return ok({"url": "", "key": "rooms/WXYZ/1/p_1a2b3c.jpg"})
