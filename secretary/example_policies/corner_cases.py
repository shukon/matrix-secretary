import itertools
import random


def get_corner_cases_policy():
    policy = {}

    policy['user_groups'] = {
        'all': {'users': ['@bot.dev:wurzelraum.org']}
    }

    policy["policy_key"] = "corner"
    policy["policy_description"] = "This policy is used to test corner cases."
    policy["default_room_settings"] = {
        "visibility": "private",
        "guest_access": "forbidden",
        "history_visibility": "invited",
        "join_rule": "public",
    }
    policy["rooms"] = {
        "Circular Space 1": {
            "room_name": "Circular Space 1",
            "is_space": True,
            "parent_spaces": ["Circular Space 2"],
            "invitees": {
                "all": 100,
            },
            'alias': 'dev_space_alias',
        },
        "Circular Space 2": {
            "room_name": "Circular Space 2",
            "is_space": True,
            "parent_spaces": ["Circular Space 1"],
            "invitees": {
                "all": 100,
            },
        },
    }
    legal_dict = {
        'guest_access': ['can_join', 'forbidden'],
        'history_visibility': ['shared', 'invited', 'joined', 'world_readable'],
        'join_rule': ['public', 'knock', 'invite', 'private', 'restricted', 'knock_restricted'],
        'visibility': ['public', 'private'],
    }

    combinations = list(itertools.product(*legal_dict.values()))
    # Add all possible combinations of legal values for the room settings
    room_names = ['Room ' + str(i + 1) for i in range(len(combinations))]
    topics = ['This is a test_room', '', 'Yeah, whatever...', 'Beep Boop Dev Room', None]
    topics = topics * (len(combinations) // len(topics) + 1)

    random.shuffle(room_names)
    for combination, name, topic in zip(combinations, room_names, topics):
        room = {
            "room_name": name,
            "invitees": {
                "all": 100,
            },
        }
        if topic is not None:
            room['topic'] = topic
        for key, value in zip(legal_dict.keys(), combination):
            room[key] = value
        policy["rooms"]["Corner Case Room " + str(combination)] = room

    return policy

