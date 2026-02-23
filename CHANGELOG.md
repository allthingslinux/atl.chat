# CHANGELOG


## v0.1.0 (2026-02-23)

### Bug Fixes

- Update LICENSE
  ([`afee623`](https://github.com/allthingslinux/bridge/commit/afee623c6725d0878c27cb23e14e3de4d9e5388a))

- Version system
  ([`1404940`](https://github.com/allthingslinux/bridge/commit/1404940b1be08873254dcf71c3174c801f2df61e))

- **ci.yml**: Update command to run semantic-release directly
  ([`edc9e93`](https://github.com/allthingslinux/bridge/commit/edc9e9324d90f6514b09fefad346f8c220d2d9b1))

- **identity**: Snake_case field names, add irc/xmpp_to_discord, fix has_irc/has_xmpp
  ([`724c29c`](https://github.com/allthingslinux/bridge/commit/724c29cc444740fac56fa3b63f26b922f7c5aba6))

- **identity.py**: Expand retry conditions to include more transient errors
  ([`0ba9dd0`](https://github.com/allthingslinux/bridge/commit/0ba9dd01386ae978efda1698cc90c88ef5585733))

- **irc.py**: Ensure puppet tasks are tracked and cleaned up properly
  ([`083e3d3`](https://github.com/allthingslinux/bridge/commit/083e3d3282ccb0c2bc6c0a56e107ae5c28fab5a2))

- **irc_puppet.py**: Use contextlib.suppress to handle asyncio.CancelledError
  ([`d6ee55e`](https://github.com/allthingslinux/bridge/commit/d6ee55e116edbbfb05baf9f109c1b9a104bd9940))

- **tests**: Add type casting for MagicMock in IRCAdapter tests
  ([`1ff1506`](https://github.com/allthingslinux/bridge/commit/1ff15061c4549cd4a704c6309c61745bb1d8756c))

- **tests**: Add type ignore comments for bus.publish lambda assignments in DiscordAdapter tests
  ([`b86a643`](https://github.com/allthingslinux/bridge/commit/b86a643ec1fb4f82bd27040349d564bcf103c5a1))

- **tests**: Enhance event assertion in test_bus_publish_reaches_targets
  ([`e82d102`](https://github.com/allthingslinux/bridge/commit/e82d102b28b3a780b4b33460e0551762df41997f))

- **tests**: Enhance IRCClient message handling tests for accuracy
  ([`0a2f908`](https://github.com/allthingslinux/bridge/commit/0a2f908281c97ca39fa222af8c8f5c8321122b9b))

- **tests**: Streamline exception handling in TestPuppetEdgeCases
  ([`5699b99`](https://github.com/allthingslinux/bridge/commit/5699b9919f0a0a182ed4b0f907fe61d01c6db63c))

- **tests**: Update exception handling in load_config test to use yaml.YAMLError
  ([`1e76c81`](https://github.com/allthingslinux/bridge/commit/1e76c818a508256e5aa83fd08e1f6f68cbb8b98d))

- **tests**: Update exception handling in TestConfigErrors to use yaml.YAMLError
  ([`1641d39`](https://github.com/allthingslinux/bridge/commit/1641d39c0905aacd107be47ac6567a9448f2d80c))

- **tests**: Update IRC client test to include ready state simulation
  ([`32a0160`](https://github.com/allthingslinux/bridge/commit/32a01608bdd13fca31f15222d4829051ef779e47))

- **tests**: Update test_echo_correlates_pending_send to remove unused variable
  ([`00eb1f0`](https://github.com/allthingslinux/bridge/commit/00eb1f0f3af5b31247a6d47f2c971147875748a0))

- **xmpp_adapter**: Extend outbound queue type to include ReactionOut
  ([`7ac8706`](https://github.com/allthingslinux/bridge/commit/7ac87066a2ce297aae3e5f93bc2f37528ba43943))

- **xmpp_component**: Add type ignore comments for pyright in message sending and MUC joining
  methods
  ([`85e054e`](https://github.com/allthingslinux/bridge/commit/85e054ee4b0aea12a88bdb2018c5a926f0af2219))

### Chores

- Add python-semantic-release as a development dependency.
  ([`74334ad`](https://github.com/allthingslinux/bridge/commit/74334ad43b233810b06710cd266b4e7705202ae8))

- Format
  ([`ebbc1bd`](https://github.com/allthingslinux/bridge/commit/ebbc1bd7ab355821dab5fe58a15539d86cb758a3))

- Update initial release config
  ([`910e521`](https://github.com/allthingslinux/bridge/commit/910e521eb97d6da8c19f625c87e1a612ec249d37))

- Update project dependencies and configuration.
  ([`b9ec50e`](https://github.com/allthingslinux/bridge/commit/b9ec50ec6fb9022f413d27df3b047cf936dbe682))

- **config**: Add .hypothesis to norecursedirs in pyproject.toml
  ([`32428a9`](https://github.com/allthingslinux/bridge/commit/32428a9fdc5afa37a8685646a957ba2bad6c46ef))

- **dependencies**: Add uvloop dependency for non-Windows platforms
  ([`819100a`](https://github.com/allthingslinux/bridge/commit/819100a8a20195bf619016d0883ee3164d065a44))

- **docs**: Update README with enhanced feature descriptions and test coverage details
  ([`f6e9fc9`](https://github.com/allthingslinux/bridge/commit/f6e9fc9ec92ff47caffd255d5e420238dee0d27c))

- **gitignore**: Add .hypothesis directory to .gitignore
  ([`97a0aa7`](https://github.com/allthingslinux/bridge/commit/97a0aa7219a6011b4885c257ea4510d2fe991da0))

- **ignore**: Add .gitignore and .cursorignore files to exclude unnecessary files and directories
  from version control
  ([`bc0f976`](https://github.com/allthingslinux/bridge/commit/bc0f976d57369fe8ac397cd6a443c873a4c91763))

- **justfile**: Add Justfile for task automation including sync, test, lint, format, and CI pipeline
  ([`0bf477a`](https://github.com/allthingslinux/bridge/commit/0bf477ac74d3d8b040e9bc1f612b8582927b8002))

- **lefthook**: Add Lefthook configuration for pre-commit commands including ruff and pytest
  ([`ba415d5`](https://github.com/allthingslinux/bridge/commit/ba415d512589977be3e1293cb39b56e46acb3058))

- **pyproject.toml**: Remove irc dependency and add pydle for IRC support
  ([`df0d1e6`](https://github.com/allthingslinux/bridge/commit/df0d1e6b36e5594195f550b0bd9e46227a99b124))

- **setup**: Add pyproject.toml and uv.lock for project configuration and dependency management
  ([`5cf7d2f`](https://github.com/allthingslinux/bridge/commit/5cf7d2f4312ba3d9de237f3bb584486260f96678))

- **workflows**: Remove manual Docker push workflow and update Docker workflow for main branch
  ([`492b535`](https://github.com/allthingslinux/bridge/commit/492b535b32252d22fe0dfc9fb05f7bce9c7c6d0a))

### Code Style

- **xmpp.py**: Remove trailing whitespace for code consistency
  ([`1513df2`](https://github.com/allthingslinux/bridge/commit/1513df2225d3fca2a0f4c50109371ab315d5d2fc))

### Continuous Integration

- Add comprehensive CI/CD workflows and Docker support
  ([`4c4332f`](https://github.com/allthingslinux/bridge/commit/4c4332f0a9c8a8fc92fedfa8847b395c437ecbe5))

### Documentation

- Add bridge QoL and customization plan
  ([`d9a3258`](https://github.com/allthingslinux/bridge/commit/d9a3258ac5230dcf84a14923dbfab9d98fe0c4f2))

- Add references-analyzer documentation for project reference analysis
  ([`08391b8`](https://github.com/allthingslinux/bridge/commit/08391b84c34408adf43c359a000d7e6fa25e699f))

- Init plan
  ([`9310238`](https://github.com/allthingslinux/bridge/commit/931023890682904b4bd29ee6398a34bccd5a218a))

- **agents**: Add comprehensive AGENTS.md documentation across project hierarchy
  ([`288f2d3`](https://github.com/allthingslinux/bridge/commit/288f2d3126dd09bf433059385190d88904594411))

- **README**: Update test count and enhance configuration details
  ([`ccbb602`](https://github.com/allthingslinux/bridge/commit/ccbb60290ee3fbd52d1ead15bd699e441f3d295e))

- **README.md**: Enhance documentation with detailed setup and feature descriptions
  ([`8d83bd6`](https://github.com/allthingslinux/bridge/commit/8d83bd60fe4895bdebd2060a495b607b5242bcba))

- **README.md**: Update architecture diagram and add data flow explanation
  ([`bd00edb`](https://github.com/allthingslinux/bridge/commit/bd00edbf9d9f24425e9560ed1972852b55a7b354))

- **README.md**: Update features and configuration for XMPP and IRCv3
  ([`aa66d92`](https://github.com/allthingslinux/bridge/commit/aa66d92d6fcc8b6bb56e4fcdc3429624e9ce3486))

- **README.md**: Update supported XEPs with message retraction and replies
  ([`c657a92`](https://github.com/allthingslinux/bridge/commit/c657a9221765e75e58050f8ce60c650f995db36f))

- **TODO.md**: Add future XEP implementations and considerations
  ([`c2d4d5d`](https://github.com/allthingslinux/bridge/commit/c2d4d5d194a5e964297c821c36b3893c256456e6))

### Features

- Add cursor commands
  ([`f92e27a`](https://github.com/allthingslinux/bridge/commit/f92e27a33e444be1e93eb03e58a502d5167b3ec4))

- **adapter**: Add base module for protocol adapters including Discord and IRC
  ([`8a48f3a`](https://github.com/allthingslinux/bridge/commit/8a48f3ab84f99bda49d49b038cb6a24221da8654))

- **adapter**: Add Discord adapter for message handling and webhook integration
  ([`6380888`](https://github.com/allthingslinux/bridge/commit/6380888f1f1f1943a5f6c8da5da3ae12a1529ef9))

- **adapter**: Implement base interface for protocol adapters with event handling methods
  ([`f671e5c`](https://github.com/allthingslinux/bridge/commit/f671e5ca642d9c2e861cc171dc518eb520434496))

- **adapter**: Implement IRC adapter for message handling and outbound queue management
  ([`3fa4eed`](https://github.com/allthingslinux/bridge/commit/3fa4eed9f379069d4fb024b305c8f0b97e673744))

- **adapter**: Implement XMPP adapter for MUC client and outbound message handling
  ([`a7a520d`](https://github.com/allthingslinux/bridge/commit/a7a520d513b8ce3f68256dea6ec1137743104477))

- **bus**: Implement Event Bus for central event dispatching among adapters
  ([`2b26226`](https://github.com/allthingslinux/bridge/commit/2b26226c6d20c4a22c12d534b9b3211932961f90))

- **bus.py**: Add _adapters property for registered adapter discovery
  ([`8dd1af4`](https://github.com/allthingslinux/bridge/commit/8dd1af412593a745c8408c82a678ba1fa12d7805))

- **ci**: Add CI workflow for linting and testing with multiple Python versions
  ([`2525282`](https://github.com/allthingslinux/bridge/commit/2525282fb11338f1e0ef4e29d98394d9848705b3))

- **config**: Add configuration management with YAML support and environment overlay
  ([`12beb2d`](https://github.com/allthingslinux/bridge/commit/12beb2df022adca743ef66b7f71fdfbc2cd96e07))

- **config**: Add example configuration file for ATL Bridge with channel mappings and settings
  ([`b8d8940`](https://github.com/allthingslinux/bridge/commit/b8d894080ddf889f10a4e706ff2a3fd816f2f93b))

- **config.example.yaml**: Add IRC configuration options for flood control, rejoin behavior, and
  SASL authentication
  ([`9033667`](https://github.com/allthingslinux/bridge/commit/9033667a402376701b8dc0e88d6bab07b5e74b57))

- **config.py**: Add IRC configuration properties for throttling, message queue, rejoin behavior,
  and SASL authentication
  ([`3edb01d`](https://github.com/allthingslinux/bridge/commit/3edb01dca040f6a013436fe7515cb7442041c0d2))

- **container**: Add Containerfile for building ATL Bridge with uv for dependency management and
  configuration
  ([`37ca9bc`](https://github.com/allthingslinux/bridge/commit/37ca9bce3eafa86ca5db5bb65eb699af023feac8))

- **disc.py**: Enhance Discord adapter with message edit and reaction handling
  ([`b193839`](https://github.com/allthingslinux/bridge/commit/b193839adeae17fa218401e335fa52b569fe3714))

- **disc.py**: Enhance DiscordAdapter to support message deletions, reactions, and typing events
  ([`9b3a878`](https://github.com/allthingslinux/bridge/commit/9b3a8788b7113b0dabb5f5b5f86d91d2579cfdb7))

- **disc.py**: Implement handling of Discord message deletions
  ([`fcf6b62`](https://github.com/allthingslinux/bridge/commit/fcf6b62af3e5321c2340870be287a1bf8ec0eadb))

- **docs**: Add README.md with project overview, features, setup instructions, and configuration
  details for ATL Bridge
  ([`65c1308`](https://github.com/allthingslinux/bridge/commit/65c1308001cc113e6abe47a3e4cec890a84369a5))

- **entrypoint**: Add main entrypoint for ATL Bridge with configuration loading, logging setup, and
  adapter initialization
  ([`c98f897`](https://github.com/allthingslinux/bridge/commit/c98f8979287ae780017a58d65bc5fe3114f358eb))

- **events**: Add optional raw parameter to reaction_in and reaction_out functions for enhanced
  event data handling
  ([`4ba5d0b`](https://github.com/allthingslinux/bridge/commit/4ba5d0b7faae8678f434c49a39664d248c9bc7ef))

- **events**: Introduce event types and dispatcher for handling inbound and outbound messages
  ([`cbbbf5d`](https://github.com/allthingslinux/bridge/commit/cbbbf5d1d5194215012d044ccf8e558aed2f4bdf))

- **events.py**: Add avatar_url attribute to MessageIn and MessageOut classes
  ([`b20017c`](https://github.com/allthingslinux/bridge/commit/b20017cafcb9abc9ca88d5bad82802152c48756f))

- **events.py**: Add support for message deletion, reactions, and typing events
  ([`42bcd55`](https://github.com/allthingslinux/bridge/commit/42bcd55e7c2a4556df9d42cdbaa200e80e6c5e5d))

- **formatting**: Add message formatting utilities for Discord and IRC
  ([`be65186`](https://github.com/allthingslinux/bridge/commit/be65186766ccf951716fd116b680ced0a943e16c))

- **gateway**: Introduce Gateway module for event bus, channel routing, and relay integration
  ([`af66452`](https://github.com/allthingslinux/bridge/commit/af664528ab261f0001c609c499bf29853d4cc6df))

- **identity**: Implement PortalClient and IdentityResolver for managing user identities across
  Discord, IRC, and XMPP with TTL caching
  ([`1d6b0f0`](https://github.com/allthingslinux/bridge/commit/1d6b0f07672f464c32c1e363319ea95d4ae920a7))

- **identity**: Restore discord_to_irc/xmpp and add portal discordId lookup
  ([`4273509`](https://github.com/allthingslinux/bridge/commit/4273509d315a1e49f83126747f28c36fa6fb86d5))

- **irc.py**: Enhance IRC client with additional IRCv3 capabilities
  ([`083e3d3`](https://github.com/allthingslinux/bridge/commit/083e3d3282ccb0c2bc6c0a56e107ae5c28fab5a2))

- **irc.py**: Implement exponential backoff and rejoin logic for IRC connections
  ([`36b02bf`](https://github.com/allthingslinux/bridge/commit/36b02bf02cceacaf1433cc3bb54a6b019138ead5))

- **irc_msgid.py**: Add IRCv3 message ID tracking with TTL cache
  ([`b58a017`](https://github.com/allthingslinux/bridge/commit/b58a017daaa2f6d9e7c790bb730da9f34d4d3be6))

- **irc_puppet**: Add IRC puppet manager for Discord users
  ([`95f89fa`](https://github.com/allthingslinux/bridge/commit/95f89fa52bae1478ad14289fa5ee9b01b69a9890))

- **irc_puppet.py**: Enhance message handling by splitting long messages
  ([`e276899`](https://github.com/allthingslinux/bridge/commit/e276899b5a5a05cdc78499c2b4969a7e0280f579))

- **irc_throttle.py**: Implement token bucket for IRC message rate limiting
  ([`70df50b`](https://github.com/allthingslinux/bridge/commit/70df50b8c8d012af21917d029a6a0b097ad1577a))

- **plans**: Add Bridge Implementation Stages plan for phased feature rollout
  ([`192f8e6`](https://github.com/allthingslinux/bridge/commit/192f8e641b0e47744d50d7f2406ea667b2b1fed2))

- **relay**: Implement Relay class for routing MessageIn to MessageOut across multiple protocols
  ([`d8a7c36`](https://github.com/allthingslinux/bridge/commit/d8a7c369f218211ebf62e0d8c1108fd4bf01dcb5))

- **relay**: Include raw event data in Relay class for improved message handling
  ([`8b9e4d9`](https://github.com/allthingslinux/bridge/commit/8b9e4d9a80058e15d1ae8434fcf2a3b9a12d6662))

- **relay.py**: Add avatar_url and raw data to event relay
  ([`688b57c`](https://github.com/allthingslinux/bridge/commit/688b57cd77734e281453c596acb3079ff2bbcd11))

- **relay.py**: Add support for IRC and XMPP message routing
  ([`a21bba2`](https://github.com/allthingslinux/bridge/commit/a21bba2c432ef81afdb8df0b420da9ebf3ebba8a))

- **relay.py**: Enhance Relay class to support message deletions, reactions, and typing events
  ([`ca6af62`](https://github.com/allthingslinux/bridge/commit/ca6af62d9f41397781b2eecfcea3684c665cf585))

- **router**: Implement channel router for mapping Discord, IRC, and XMPP channels
  ([`0adc4d5`](https://github.com/allthingslinux/bridge/commit/0adc4d595770eb019ca702e12246de2a0122b7f4))

- **tests**: Add comprehensive test suite for configuration, events, gateway, and Discord adapter
  functionality
  ([`94ab1c3`](https://github.com/allthingslinux/bridge/commit/94ab1c306a6bf3953b600cffe1627dd97a7f5c02))

- **tests**: Add comprehensive test suite for IRCAdapter event handling
  ([`9f9231f`](https://github.com/allthingslinux/bridge/commit/9f9231f4d32946db74d694e1fb0ff72881c9f151))

- **tests**: Add comprehensive test suite for IRCClient event handling
  ([`bc023a2`](https://github.com/allthingslinux/bridge/commit/bc023a2daae9471ff5d373310f1c74215416a307))

- **tests**: Add comprehensive test suite for IRCPuppetManager functionality
  ([`49d8d34`](https://github.com/allthingslinux/bridge/commit/49d8d34663cc00d6ef7c27667cdfc6ea0289cbd1))

- **tests**: Add comprehensive tests for DiscordAdapter event handling
  ([`7eb1a9d`](https://github.com/allthingslinux/bridge/commit/7eb1a9d910c3dbf0c4b36d3fa666f378736b931f))

- **tests**: Add comprehensive tests for message formatting between Discord and IRC
  ([`f1f324b`](https://github.com/allthingslinux/bridge/commit/f1f324b3fdeeebf1581feb864f54c80b91268271))

- **tests**: Add extended relay tests for untested paths in relay.py
  ([`b095e4f`](https://github.com/allthingslinux/bridge/commit/b095e4fbe8fa68cfa367f6b2aba23838f2878448))

- **tests**: Add new event types to test suite for improved coverage
  ([`96ad72f`](https://github.com/allthingslinux/bridge/commit/96ad72fc470172b8598c1298a60deffcf53f81f3))

- **tests**: Add unit tests for IRC message ID tracking and mapping
  ([`057e255`](https://github.com/allthingslinux/bridge/commit/057e2559c5497f2cd0aaa5ae6ee2fcc0d76dff2b))

- **tests**: Add unit tests for XMPP message ID tracking and mapping
  ([`4f4c527`](https://github.com/allthingslinux/bridge/commit/4f4c527d5c6c1acc3c50b22fded1ae4fc530b7d6))

- **tests**: Enhance event dispatcher and bus tests for robustness
  ([`c276fd7`](https://github.com/allthingslinux/bridge/commit/c276fd7d8f33096564008caee2a24e0337e345c6))

- **tests**: Expand test suite for relay message handling and formatting
  ([`4ee24f1`](https://github.com/allthingslinux/bridge/commit/4ee24f1e8061a239101ea9da54739e47b4db05db))

- **tests**: Update avatar sync tests to validate URL preservation and uniqueness
  ([`398bbd0`](https://github.com/allthingslinux/bridge/commit/398bbd073612d89ef596b395d9549e6f901c08fe))

- **todos**: Expand TODO list with high and medium priority tasks for IRC features
  ([`bc8bbe2`](https://github.com/allthingslinux/bridge/commit/bc8bbe2a01b7859f50ff03b969ca05a5480cc155))

- **vscode**: Add VSCode settings for Python, shell scripting, and markdown formatting
  ([`753ca9c`](https://github.com/allthingslinux/bridge/commit/753ca9c7df23e7285dad4c02d69fd13f049df11f))

- **xmpp.py**: Enhance XMPPAdapter to support message deletions and reactions
  ([`ec96824`](https://github.com/allthingslinux/bridge/commit/ec968242b992feee440722ee51ab9b6fbeb7680b))

- **xmpp_component**: Add XMPP component for Discord user integration
  ([`68d9b6f`](https://github.com/allthingslinux/bridge/commit/68d9b6f353631c750fa89dfe6763bf4e1e132967))

- **xmpp_component.py**: Add support for message retraction and replies using XEP-0424 and XEP-0461
  ([`549de78`](https://github.com/allthingslinux/bridge/commit/549de784a7e456e443e8e76f9a4f485321ed4904))

- **xmpp_component.py**: Implement reaction handling and message deletion for XMPP
  ([`4704f6a`](https://github.com/allthingslinux/bridge/commit/4704f6a51c9aa0ec909d15a88f92f2c4b3e2ab3c))

- **xmpp_msgid.py**: Add XMPP message ID tracking with TTL cache
  ([`bf70043`](https://github.com/allthingslinux/bridge/commit/bf700438458badc92fe73f6bab3e808eb7e14fb8))

### Refactoring

- Implement `TTLCache` for avatar and webhook caches and reuse `aiohttp.ClientSession` for HTTP
  requests.
  ([`27a522f`](https://github.com/allthingslinux/bridge/commit/27a522f07eca55914705f33382d30807cb1dada4))

- **bridge**: Add ping interval and prejoin commands to IRCAdapter initialization
  ([`c53095d`](https://github.com/allthingslinux/bridge/commit/c53095d3f7ae3a651ad3103abfc473e019ac8d5c))

- **bridge**: Enhance async main execution with uvloop support
  ([`4af46fa`](https://github.com/allthingslinux/bridge/commit/4af46faa69a8cc2908f26f192bd64cc84584243d))

- **bridge**: Enhance IRCPuppet initialization with ping interval and prejoin commands
  ([`c3f681c`](https://github.com/allthingslinux/bridge/commit/c3f681c220bfd4ec40fa5ec13d8f337ad34c3e46))

- **bridge**: Introduce Adapter protocol for type safety and clarity
  ([`9f0c667`](https://github.com/allthingslinux/bridge/commit/9f0c66702b22edcd5e5d21635cb8a9a5c4c82a7c))

- **config**: Add properties for IRC puppet ping interval and prejoin commands
  ([`6b5d667`](https://github.com/allthingslinux/bridge/commit/6b5d667aa4867807fb612e2394b27f39f1809cd1))

- **config**: Update exclusion list in pyproject.toml to include 'references'
  ([`14634a8`](https://github.com/allthingslinux/bridge/commit/14634a8223103096c7db8354a62c7e9c6d8d7a2b))

- **cursorignore**: Simplify references exclusion pattern
  ([`9bf52ad`](https://github.com/allthingslinux/bridge/commit/9bf52adae42920167441bca3dbc565c7bfe12269))

- **discord**: Update message handling to use raw events for edits, deletes, and bulk deletes
  ([`8a7c8af`](https://github.com/allthingslinux/bridge/commit/8a7c8afbd9c71e777578cd4ce15a4fa1937c2151))

- **irc.py**: Migrate IRC adapter to use pydle with IRCv3 support
  ([`9137497`](https://github.com/allthingslinux/bridge/commit/9137497ae86f3dafa09393a38528f98f6d55e4d3))

- **irc.py**: Use contextlib.suppress for cleaner task cancellation
  ([`083e3d3`](https://github.com/allthingslinux/bridge/commit/083e3d3282ccb0c2bc6c0a56e107ae5c28fab5a2))

- **justfile**: Streamline task definitions and enhance testing commands
  ([`fb19075`](https://github.com/allthingslinux/bridge/commit/fb19075c6eb68e6540ae8cbeb560a3f44a56f7a9))

- **tests**: Add comprehensive tests for PortalClient identity retrieval
  ([`3d835dc`](https://github.com/allthingslinux/bridge/commit/3d835dcdb0fa49e90648c4777a47273e16c6d146))

- **tests**: Add new tests for IRC to Discord formatting and message splitting
  ([`1083ba5`](https://github.com/allthingslinux/bridge/commit/1083ba5925b145d35de63fa076d674922855b4d4))

- **tests**: Add tests for consumer guard conditions in XMPP adapter
  ([`7c12d9b`](https://github.com/allthingslinux/bridge/commit/7c12d9b21bd32932263e24f88c576121901e66f4))

- **tests**: Add tests for content filtering and skip-target conditions in message relay
  ([`c9c1179`](https://github.com/allthingslinux/bridge/commit/c9c11797649e1aa2bcce16958e3c86b2aae55321))

- **tests**: Add tests for IRC client connection and message handling
  ([`2c79440`](https://github.com/allthingslinux/bridge/commit/2c79440391ac8e2e7da5ce7cd43de7383d5c68d7))

- **tests**: Add tests for IRC puppet ping interval and prejoin commands
  ([`1e050e2`](https://github.com/allthingslinux/bridge/commit/1e050e2d2327fa4d3d15990dd0b13cada124b794))

- **tests**: Clean up imports and improve code readability
  ([`ba5bc3f`](https://github.com/allthingslinux/bridge/commit/ba5bc3fdb7d5cfd3171038d4b6f370329b47ce1f))

- **tests**: Consolidate warning filter declaration in test_xmpp_component.py
  ([`846e108`](https://github.com/allthingslinux/bridge/commit/846e108c026ce6ef289a379b0c9e6f82b1e3ce60))

- **tests**: Enhance assertions in TestChannelRouter for improved clarity
  ([`b988f46`](https://github.com/allthingslinux/bridge/commit/b988f46132f5dbe5a1317a9c8771d611f3eefd52))

- **tests**: Enhance IRCPuppet tests for ping interval and prejoin commands
  ([`a67a0c3`](https://github.com/allthingslinux/bridge/commit/a67a0c3dec3f8449b8e46de0831bd7cdca434e65))

- **tests**: Enhance type casting and event type annotations in XMPP adapter tests
  ([`dc5ac60`](https://github.com/allthingslinux/bridge/commit/dc5ac60b6e8f1295168f4d7a586dfedb87303d17))

- **tests**: Improve coroutine handling in IRC adapter tests
  ([`8f176ef`](https://github.com/allthingslinux/bridge/commit/8f176effbdab0257fb6d8a78ead59b5e78a81c7d))

- **tests**: Improve type assertion in TestPresenceEventComparison
  ([`8a0723b`](https://github.com/allthingslinux/bridge/commit/8a0723b600d792e3f64c4de045ef5cec7b43fb62))

- **tests**: Remove unused import in test_file_transfers.py
  ([`50bec53`](https://github.com/allthingslinux/bridge/commit/50bec5358d9ce871080a3b37a9e4e574969d982f))

- **tests**: Remove unused import of pytest in test_irc_threading.py
  ([`318e458`](https://github.com/allthingslinux/bridge/commit/318e4581441126fcf0d23f386575895d75363e83))

- **tests**: Remove unused import of pytest in test_message_formatting.py
  ([`3634f0b`](https://github.com/allthingslinux/bridge/commit/3634f0bb697e806594e0f8afe0601d7891c48848))

- **tests**: Remove unused import of pytest in test_xmpp_features.py
  ([`d8e921e`](https://github.com/allthingslinux/bridge/commit/d8e921e35c34daae54bdb04d14cadffb07c79221))

- **tests**: Remove unused MockMsg instance in TestOnGroupchatMessage
  ([`9627aeb`](https://github.com/allthingslinux/bridge/commit/9627aebedb85a933103f6237d8f2459b059b3ecd))

- **tests**: Remove unused variables in TestIRCToXMPP and TestXMPPToIRC
  ([`a2d2377`](https://github.com/allthingslinux/bridge/commit/a2d2377527af96681f98d1f2918803c4177a7c67))

- **tests**: Simplify Config tests by removing redundant code and adding parameterized tests
  ([`9c74319`](https://github.com/allthingslinux/bridge/commit/9c74319db275ef118c2635a9f4eb3cc67793e2c7))

- **tests**: Simplify event type checking in MockAdapter
  ([`f1ac848`](https://github.com/allthingslinux/bridge/commit/f1ac848a5f87b9ccb67e85f25be9781c69822d8c))

- **tests**: Streamline IdentityResolver tests with helper function
  ([`1cbfe49`](https://github.com/allthingslinux/bridge/commit/1cbfe4991fe6c5c4b099ddd5a14d512cd9e3fce9))

- **tests**: Update DiscordAdapter tests to utilize raw event payloads for message edits and
  deletions
  ([`4cff867`](https://github.com/allthingslinux/bridge/commit/4cff86717e523e565aac782cb1d12056b8141a27))

- **tests**: Update IRCPuppet test mocks for clarity and consistency
  ([`f9cef73`](https://github.com/allthingslinux/bridge/commit/f9cef7391f57cf32fe9ac6743a67365503eef616))

- **xmpp.py**: Replace XMPP client with XMPP component for multi-presence support
  ([`bcc50b2`](https://github.com/allthingslinux/bridge/commit/bcc50b2fa0fc8ddd013526e6f8ead7ec3017ce35))

### Testing

- Add comprehensive test suite for bridge functionality
  ([`81a74dc`](https://github.com/allthingslinux/bridge/commit/81a74dc14ce550ed2b6ab352b8b0be608f2952dd))

- Standardize test cases across multiple modules to follow the Arrange, Act, Assert pattern for
  improved clarity.
  ([`875dba4`](https://github.com/allthingslinux/bridge/commit/875dba455f388d5a84c9047b150ebfe64f66b887))

- **avatar_sync, file_transfers, irc_threading, message_formatting, presence_events, xmpp_features,
  xmpp_msgid**: Add comprehensive test coverage for various features
  ([`cfbdd62`](https://github.com/allthingslinux/bridge/commit/cfbdd626ffe28ff87927804bb772252597128ccb))

- **config**: Add yaml.scanner.ScannerError to expected exceptions
  ([`5dc6ec9`](https://github.com/allthingslinux/bridge/commit/5dc6ec9e9526f316a45e75afa2149e77e0c3f313))

- **relay, retry, router**: Add comprehensive unit tests for relay routing, retry logic, and channel
  router
  ([`81a74dc`](https://github.com/allthingslinux/bridge/commit/81a74dc14ce550ed2b6ab352b8b0be608f2952dd))

- **retry_logic**: Simplify retry logic test assertions
  ([`5dc6ec9`](https://github.com/allthingslinux/bridge/commit/5dc6ec9e9526f316a45e75afa2149e77e0c3f313))

- **tests**: Add comprehensive test suite for XMPPAdapter functionality
  ([`adfab42`](https://github.com/allthingslinux/bridge/commit/adfab42a9637963012acbddb0f8248c1193002bd))

- **tests**: Add comprehensive test suite for XMPPComponent event handlers
  ([`0607707`](https://github.com/allthingslinux/bridge/commit/06077074b0c63f914126a33d22686f110d1293d4))

- **tests**: Add tests for XMPPMessageIDTracker functionality
  ([`bff3f65`](https://github.com/allthingslinux/bridge/commit/bff3f65e8196f9e004fc84e22efb30ed0a558a1c))

- **tests**: Enhance avatar URL tests with additional assertion
  ([`f2ae418`](https://github.com/allthingslinux/bridge/commit/f2ae41857bd575e38264705a7f48bb8b5455c7fd))

- **tests**: Enhance message editing test to verify is_edit flag preservation
  ([`ebefe6d`](https://github.com/allthingslinux/bridge/commit/ebefe6d92cd7543ecc35339def5ee4ecd8a7766a))

- **tests**: Enhance message event tests with additional scenarios and attributes
  ([`5ee106e`](https://github.com/allthingslinux/bridge/commit/5ee106e34d36254dcf333a88f709f85f64d96597))

- **tests**: Expand Config tests to cover additional properties and defaults
  ([`5d26610`](https://github.com/allthingslinux/bridge/commit/5d26610acdd75f2af8ab85f6ffb4744a62a41413))

- **tests**: Expand IdentityResolver tests for Discord and XMPP functionality
  ([`494c920`](https://github.com/allthingslinux/bridge/commit/494c9204fc394e17654b98ed37058b686bb0a6ef))

- **tests**: Refactor ChannelRouter tests for clarity and coverage
  ([`1f30cc3`](https://github.com/allthingslinux/bridge/commit/1f30cc3b72485a64e3c01cd100e7f4800b31b5d7))

- **tests**: Refactor Discord to IRC tests with parameterized cases
  ([`ea89363`](https://github.com/allthingslinux/bridge/commit/ea8936315fc64cb0ae18c423815798e4399a2dd2))

- **tests**: Update relay tests to verify message content and author attributes
  ([`4bf804a`](https://github.com/allthingslinux/bridge/commit/4bf804a37424dc0dbd6d009df2314928e79c3529))
