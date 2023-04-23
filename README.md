# matrix-secretary

**Currently proof-of-concept. Not ready for production use.**

Matrix-Secretary is a Maubot implementation that allows you to automate tasks in your Matrix homeserver. With the help of json-policies, you can create and manage rooms, invite users, manage power-levels, kick or ban users, and even manage bots and bridges for rooms.

## Features

- [ ] ACL for bot-usage
- [ ] Add policy
  - [ ] Validate policy
- [x] Remove policy
  - [x] Remove all rooms created by policy
- [x] Clean up unused rooms on command
- [x] Create rooms from json-policy
  - [x] Create room
  - [ ] Set room name
  - [ ] Set room topic
  - [ ] Set room avatar
  - [ ] Set room visibility
  - [ ] Set room join rules
  - [ ] Set room history visibility
  - [ ] Set room guest access
  - [ ] Set room encryption
  - [ ] Define room aliases
  - [ ] Organize rooms in spaces
- [x] Manage users from json-policy
  - [x] Invite user
  - [x] Set power-levels
  - [ ] Kick user
  - [ ] Ban user
  - [ ] Unban user
  - [ ] Expand user-groups
- [ ] Perform bot-actions
  - [ ] One-Shot
  - [ ] Periodic
  - [ ] On-Event
- [ ] Manage bridges
    - [ ] Manage 

## Installation

Use the [maubot plugin manager](https://github.com/maubot/maubot) to install the mbc-release.

## Usage


## Examples
You can find sample policies in the [policies](secretary/example_policies/) directory.

### Nina Warnapp

[Nina Warnapp](https://warnung.bund.de/) is a German catastrophe-protection app. With Matrix-Secretary, you can automatically create a policy that generates a room per warn region and automatically subscribes to the corresponding RSS feed using a RSS-bot.
