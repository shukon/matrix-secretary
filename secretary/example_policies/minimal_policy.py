def get_minimal_policy():
    return {
        "policy_key": "minimal_policy",
        "policy_description": "This is a minimal policy that creates a single room with a single user.",
         "default_room_settings": {
            "visibility": "private",
            "guest_access": "forbidden",
            "history_visibility": "invited",
            "join_rule": "public",
        },
        "rooms": {
            "spaaaaaaace": {
                "room_name": "Space",
                "is_space": True,
                "invitees": {
                    "@shukon:wurzelraum.org": 100,
                },
            },
            "solar_system": {
                "room_name": "Sunshine and rainbows",
                "is_space": True,
                "parent_spaces": ["spaaaaaaace"],
                "invitees": {
                    "@shukon:wurzelraum.org": 100,
                },
            },
            "neptune": {
                "room_name": "a rooms of one's own",
                "alias": "e xample_neptune",
                "topic": "It's all about ice giants.",
                "invitees": {
                    "@shukon:wurzelraum.org": 100,
                },
                'join_rule': 'public',
                'parent_spaces': ['spaaaaaaace', 'solar_system'],
                'history_visibility': 'invited',
                'guest_access': 'can_join',
            },
        },
    }