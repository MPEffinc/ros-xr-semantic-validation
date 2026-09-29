# xiaoxiaoxh semantic map

Controller pose, buttons, commands and Unity local time are serialized. The observed send path
does not preserve or revalidate tracking validity/confidence/source identity. `valid=true` is an
application field, not demonstrated native tracking validity. Downstream control code uses poses
and trigger state; this audit has not established an equivalent tracking gate. E1 only; no
vulnerability or physical-consequence claim follows.
