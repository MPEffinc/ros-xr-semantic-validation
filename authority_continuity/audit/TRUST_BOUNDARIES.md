# Trust Boundaries

| # | Boundary | What is checked there (source) | What is *not* checked | Label |
|---|---|---|---|---|
| TB1 | Network → HorusLink bridge | HELLO: role=UnityClient, lane, session_id≠0 | any credential; TLS; operator identity | SOURCE_CONFIRMED |
| TB2 | Client message → lease/catalog state | JSON well-formedness; for catalog `role∈{host,single}` (self-asserted) | who is allowed to be host; catalog vs. active leases | SOURCE_CONFIRMED |
| TB3 | Client data frame → ROS publish | `authorize_command_publish` (protected topic + active lease + holder connection) | unprotected topics, unleased robots, service calls | SOURCE_CONFIRMED |
| TB4 | Bridge → ROS graph | nothing HORUS-specific; SROS2 could authenticate the *bridge process* (enclave) if deployed | per-operator identity (bridge is one principal) | SOURCE_CONFIRMED (HORUS); SROS2 per design doc, see `EXISTING_DEFENSES.md` |
| TB5 | ROS topic → backend Nav2 adapter | none | who published goal/cancel; lease state | SOURCE_CONFIRMED |
| TB6 | Backend → Nav2 action server | ROS 2 action protocol (goal UUID) | originator; ownership of a goal | SOURCE_CONFIRMED (HORUS side); ROS action semantics see `EXISTING_DEFENSES.md` |
| TB7 | Controller → actuator | controller-local timeouts/limits if configured | — | outside HORUS; NOT_VERIFIED per deployment |

## Consequence for the threat model

Because TB1 admits any network peer and TB2 trusts self-asserted roles, the bridge's lease is
**not an access-control boundary against a non-cooperating client** in the implemented system:
any peer that can reach TCP 10000 is a "client" with the same capabilities as the HORUS app.
Any attack that requires "an authenticated operator abusing authority" therefore collapses into
the known problem "unauthenticated bridge on a reachable network" (cf. rosbridge / ROS-TCP-Endpoint
class). This is recorded here so later phases do not invent an authenticated principal that does
not exist (RESEARCH_PLAN K4).

The boundaries where the *candidate question* (consistency of authority vs. execution among
cooperative operators) can meaningfully be asked are TB3→TB6: lease end/transfer at TB3 is not
reflected at TB5/TB6.
