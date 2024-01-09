Messages when the bot is added and made admin
1. `my_chat_member`
2. `message` With a `new_chat_participant`

```json
{
  "ok": true,
  "result": [
    {
      "update_id": 448152148,
      "my_chat_member": {
        "chat": {
          "id": -4008338308,
          "title": "RejuganBotTestingChannel",
          "type": "group",
          "all_members_are_administrators": true
        },
        "from": {
          "id": 77629777,
          "is_bot": false,
          "first_name": "Javier",
          "last_name": "(graffic)",
          "username": "graffic"
        },
        "date": 1694899102,
        "old_chat_member": {
          "user": {
            "id": 6596880317,
            "is_bot": true,
            "first_name": "rejubot",
            "username": "RejuganBot"
          },
          "status": "left"
        },
        "new_chat_member": {
          "user": {
            "id": 6596880317,
            "is_bot": true,
            "first_name": "rejubot",
            "username": "RejuganBot"
          },
          "status": "member"
        }
      }
    },
    {
      "update_id": 448152149,
      "message": {
        "message_id": 3,
        "from": {
          "id": 77629777,
          "is_bot": false,
          "first_name": "Javier",
          "last_name": "(graffic)",
          "username": "graffic"
        },
        "chat": {
          "id": -4008338308,
          "title": "RejuganBotTestingChannel",
          "type": "group",
          "all_members_are_administrators": true
        },
        "date": 1694899102,
        "new_chat_participant": {
          "id": 6596880317,
          "is_bot": true,
          "first_name": "rejubot",
          "username": "RejuganBot"
        },
        "new_chat_member": {
          "id": 6596880317,
          "is_bot": true,
          "first_name": "rejubot",
          "username": "RejuganBot"
        },
        "new_chat_members": [
          {
            "id": 6596880317,
            "is_bot": true,
            "first_name": "rejubot",
            "username": "RejuganBot"
          }
        ]
      }
    },
    {
      "update_id": 448152150,
      "my_chat_member": {
        "chat": {
          "id": -4008338308,
          "title": "RejuganBotTestingChannel",
          "type": "group",
          "all_members_are_administrators": true
        },
        "from": {
          "id": 77629777,
          "is_bot": false,
          "first_name": "Javier",
          "last_name": "(graffic)",
          "username": "graffic"
        },
        "date": 1694900283,
        "old_chat_member": {
          "user": {
            "id": 6596880317,
            "is_bot": true,
            "first_name": "rejubot",
            "username": "RejuganBot"
          },
          "status": "member"
        },
        "new_chat_member": {
          "user": {
            "id": 6596880317,
            "is_bot": true,
            "first_name": "rejubot",
            "username": "RejuganBot"
          },
          "status": "administrator",
          "can_be_edited": false,
          "can_manage_chat": true,
          "can_change_info": true,
          "can_delete_messages": true,
          "can_invite_users": true,
          "can_restrict_members": true,
          "can_pin_messages": true,
          "can_promote_members": false,
          "can_manage_video_chats": true,
          "is_anonymous": false,
          "can_manage_voice_chats": true
        }
      }
    }
  ]
}
```