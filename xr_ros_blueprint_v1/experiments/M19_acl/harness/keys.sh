#!/usr/bin/env bash
# M19 keystores (run once per campaign, as root, in the trial image; output under the ignored host dir mounted at /keys).
# One keystore per deployment. Enclaves: /m19/controller /m19/mux /m19/observer /m19/app.
#   D_OPEN:     every enclave with the sros2 default permissions (allow all), i.e. the app holds a valid key that may
#               publish anywhere.
#   D_RESTRICT: the same, except /m19/app gets permissions generated from policies/app_restricted.xml.
# Ownership: each enclave dir belongs to the uid that runs that process (app 2001, mux 2002, controller 2003,
# observer 2004), mode 0700; the CA private keys stay root-only. Key material is never printed.
set -e; source /opt/ros/jazzy/setup.bash
for D in D_OPEN D_RESTRICT; do
  K=/keys/$D/ks; rm -rf /keys/$D; mkdir -p /keys/$D
  ros2 security create_keystore $K > /keys/$D/create.log 2>&1
  for e in controller mux observer app; do ros2 security create_enclave $K /m19/$e >> /keys/$D/create.log 2>&1; done
  if [ $D = D_RESTRICT ]; then ros2 security create_permission $K /m19/app /m19/policies/app_restricted.xml >> /keys/$D/create.log 2>&1; fi
  chmod 755 /keys /keys/$D $K $K/enclaves $K/enclaves/m19; chmod -R a+rX $K/public
  chmod 700 $K/private
  for p in app:2001 mux:2002 controller:2003 observer:2004; do e=${p%%:*}; u=${p##*:}
    chown -R $u:$u $K/enclaves/m19/$e; chmod 700 $K/enclaves/m19/$e; chmod 600 $K/enclaves/m19/$e/key.pem; done
  sha256sum $K/enclaves/m19/app/permissions.xml | cut -c1-16 > /keys/$D/app_permissions.sha16
done
chown -R root:root /keys/*/create.log; echo keys_ok
