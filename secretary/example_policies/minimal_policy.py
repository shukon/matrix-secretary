def get_minimal_policy():
    return {
        "policy_key": "minimal_policy",
        "policy_description": "This is a minimal policy that creates a single room with a single user.",
        "rooms": {
            "room1": {
                "room_name": "Room 1",
                "room_alias": "room1",
                "room_topic": "This is room 1.",
                "invitees": {
                    "@shukon:wurzelraum.org": 100,
                },
            },
        },
    }