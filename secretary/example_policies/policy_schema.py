import json

SCHEMA = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "0.1-matrix-secretary-schema.json
  "title": "Matrix Secretary Schema",
  "description": "Schema for defining a Matrix ecosystem, including rooms, actions, and user groups.",
  "type": "object",
  "properties": {
    "schemaVersion": {
      "description": "The version of the schema used to validate this file.",
      "type": "number",
      "minimum": 0.1,
      "maximum": 1.0
    },
    "policy_key": {
      "description": "Identification information for the ecosystem.",
      "type": "string"
    },
    "default_room_settings": {
      "description": "Default settings for new rooms.",
      "type": "object",
      "properties": {
        "visibility": {
          "description": "The default visibility of new rooms.",
          "type": "string",
          "enum": [
            "public",
            "private"
          ]
        },
        "guest_access": {
          "description": "Whether guests are allowed to join new rooms.",
          "type": "boolean"
        },
        "history_visibility": {
          "description": "The default history visibility of new rooms.",
          "type": "string",
          "enum": [
            "invited",
            "joined",
            "shared",
            "world_readable"
          ]
        },
        "visibility": {
          "description": "The default visibility of new rooms.",
          "type": "string",
          "enum": [
            "public",
            "private"
          ]
        },
        "join_rule": {
          "description": "The default join rule of new rooms.",
          "type": "string",
          "enum": [
            "public",
            "knock",
            "invite",
            "private"
          ]
        }
      },
      "additionalProperties": false
    },
    "rooms": {
      "description": "The rooms in the ecosystem.",
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "alias": {
            "description": "The Matrix alias for the room.",
            "type": "string",
            "format": "matrix-room"
          },
          "active": {
            "description": "Whether the room is currently active.",
            "type": "boolean"
          },
          "room_name": {
            "description": "The name of the room.",
            "type": "string"
          },
          "room_id": {
            "description": "The Matrix room ID for the room.",
            "type": "string",
          },
          "invitees": {
            "description": "A mapping of users/user groups to their power levels for this room.",
            "type": "object",
            "additionalProperties": {
              "type": "integer",
              "minimum": 0,
              "maximum": 100
            }
          },
          "is_space": {
            "description": "Whether the room is a space.",
            "type": "boolean"
          },
          "parent_spaces": {
            "description": "A list of Matrix room IDs for parent spaces of this room.",
            "type": "array",
            "items": {
              "type": "string",
              "format": "matrix-room"
            }
          },
          "topic": {
            "description": "The topic of the room.",
            "type": "string"
          },
          "suggested": {
            "description": "Whether this room is suggested to users.",
            "type": "boolean"
          },
          "join_rule": {
            "description": "The join rule of the room.",
            "type": "string",
            "enum": [
              "public",
              "knock",
              "invite",
              "private"
            ]
          },
          "visibility": {
            "description": "The visibility of the room.",
            "type": "string",
            "enum": [
              "public",
              "private"
            ]
          },
          "guest_access": {
            "description": "Whether guests are allowed to join the room.",
            "type": "boolean"
          },
          "history_visibility": {
            "description": "The history visibility of the room.",
            "type": "string",
            "enum": [
              "invited",
              "joined",
              "shared",
              "world_readable"
            ]
          },
          "room_type": {
            "description": "The type of the room.",
            "type": "string",
            "enum": [
              "m.space",
              "m.room"
            ]
          },
          "avatar_url": {
            "description": "The avatar URL of the room.",
            "type": "string",
            "format": "uri"
          },
          "bot_actions": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "properties": {
                "template": {
                  "type": "string"
                },
                "arguments": {
                  "type": "object",
                  "additionalProperties": {
                    "type": "string"
                  }
                }
              },
              "required": [
                "template"
              ]
            }
          }
        }
      }
    },
    "bot_actions": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string"
          },
          "bots": {
            "type": "array",
            "items": {
              "type": "string",
              "format": "matrix-user",
              "description": "The Matrix user ID of the bot.",
              "pattern": "^@.*:.*$",
              "examples": [
                "@bot:example.com"
              ]
            }
          },
          "commands": {
            "type": "array",
            "items": {
              "type": "string",
              "description": "The command name."
            }
          },
          "sub_bot_actions": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "properties": {
                "template": {
                  "type": "string"
                },
                "arguments": {
                  "type": "object",
                  "additionalProperties": {
                    "type": "string"
                  }
                }
              },
              "required": [
                "template"
              ]
            }
          }
        },
        "required": [
          "template"
        ]
      }
    },
    "user_groups": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string"
          },
          "users": {
            "type": "array",
            "items": {
              "type": "string",
              "format": "matrix-user",
              "description": "The Matrix user ID of the user.",
              "pattern": "^@.*:.*$",
              "examples": [
                "@user:example.com"
              ]
            }
          }
        }
      }
    }
  },
  "required": [
    "policy_key"
  ]
}
"""


def get_schema():
    return json.loads(SCHEMA)
