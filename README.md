# Gendome for Home Assistant

Gendome is a cloud-polling Home Assistant custom integration for Gendome Home
3000 and Go series energy devices. Version 1.0 implements OAuth2 account
linking, device discovery, coordinated state polling, safe device controls,
scheduled-charging enable/disable, and privacy-safe diagnostics.

The V1.0 launch path intentionally uses HACS for distribution and a standard
browser-based OAuth2 Authorization Code + PKCE flow for account linking.

## Supported entities

| Platform | Entities |
| --- | --- |
| Sensor | Battery SOC, one dynamically named charge/discharge remaining-time entity, input/AC/solar/output/AC output/DC output power, AC charge power setting |
| Optional sensor | Wind input power, firmware version |
| Binary sensor | Online, charging, discharging |
| Switch | AC output, DC output, scheduled charging |
| Optional switch | AC input and buzzer (created only when the API exposes the corresponding state) |
| Number | AC charge power limit, battery protection lower SOC, battery protection upper SOC |
| Button | Refresh state |

Entities use `mac + entity_key` as their stable unique ID. Controls are not
optimistic: the integration waits for the Java OpenAPI command result and then
refreshes the coordinated device state.

## V1.0 user journey

1. Install **Gendome** from HACS and restart Home Assistant.
2. Open **Settings → Devices & services → Add integration → Gendome**.
3. Home Assistant opens the Gendome authorization website in the browser.
4. Sign in with the Gendome account, review the requested permissions, and
   select **Allow**.
5. Gendome redirects the browser back to Home Assistant. The integration then
   discovers the devices already bound to that Gendome account.

## User prerequisites

- Home Assistant 2024.8 or newer;
- HACS installed and working;
- a Gendome account with at least one supported device already bound;
- internet access from the browser and Home Assistant server to Gendome cloud
  services.

To use the **Scheduled charging** switch, first create a charging plan in the
Gendome app. V1.0 can read and enable/disable an existing plan, but it cannot
create or edit the plan in Home Assistant.

## Production backend prerequisites

The Gendome backend must provide the endpoints documented in
[`docs/openapi-contract.md`](docs/openapi-contract.md), and a public OAuth client
with:

- client ID `gendome_home_assistant` and no client secret;
- grant types `authorization_code` and `refresh_token`;
- mandatory PKCE using `S256` for the authorization-code flow;
- the fixed `https://my.home-assistant.io/redirect/oauth` redirect URI;
- read scopes `device:read`, `statistics:read`, and
  `scheduled_charging:read`;
- optional control scopes `device:control:switch`,
  `device:control:setting`, and `scheduled_charging:write`.

The public client ID is safe to ship in the integration. It must never have a
client secret because every HACS installation can inspect the source code.

## Installation with HACS

For the initial V1.0 rollout, install the integration as a HACS custom
repository:

1. In HACS, open **Integrations**, then **Custom repositories**.
2. Add `https://github.com/gendome/home-assistant.git` with category
   **Integration**.
3. Find and install **Gendome**, then restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Gendome** and
   complete the browser authorization flow.

After the repository is accepted into the default HACS catalog, users can
search for **Gendome** directly in HACS and the custom-repository steps are no
longer needed.

Adding the integration immediately opens the Gendome website. Sign in, review
the requested access, and select **Allow**. Gendome then returns to Home
Assistant, which creates the config entry and loads the account's devices.
Users do not create OAuth credentials and do not see an implementation picker.
The Gendome password is entered only on the Gendome-owned authorization page;
it is not entered into or stored by Home Assistant.

This HACS flow uses Gendome's built-in public OAuth client with Authorization
Code + PKCE; it does not depend on Nabu Casa Cloud Account Linking.

For a manual installation, copy `custom_components/gendome` into the Home
Assistant `config/custom_components` directory and restart Home Assistant.

## Safety behavior

- Device commands use a new idempotency key and poll `commandId` for a terminal
  result.
- Offline devices are unavailable for control; the Online binary sensor remains
  available so it can report `off`.
- Battery protection requires `0 ≤ lower SOC < upper SOC ≤ 100` both in Home
  Assistant and on the backend.
- AC charge power gets a Home Assistant model limit for Home 3000, Go 300,
  Go 800, GO1000 (60–1000 W), and GO2000 (60–1500 W); the backend remains
  authoritative.
- GO1000 and GO2000 battery protection limits follow the device protocol:
  lower SOC 0–30%, upper SOC 50–100%, both in 10% steps.
- Turning off AC or DC output can immediately interrupt connected loads.

## Diagnostics and troubleshooting

Download diagnostics from the Gendome integration page. Tokens, email, IP,
serial number, MAC, and device IDs are redacted or masked. See
[`docs/troubleshooting.md`](docs/troubleshooting.md) for common failures.

## Known V1.0 limitations

- The integration is distributed through HACS and is not bundled with Home
  Assistant Core.
- Full scheduled-charging rule editing is intentionally excluded; only an
  existing plan can be read and enabled/disabled.
- Buzzer support stays hidden until the backend returns its semantic state.
- Storm, TOU, self-consumption, reserve SOC, forced discharge, factory reset,
  UPS protection changes, and OTA are not exposed.
- Remaining-time values use minutes. Home Assistant creates one stable entity:
  its displayed name is **Charge remaining time** while `charging` is true and
  **Discharge remaining time** while `charging` is false or unknown.
- Charging is derived only from `inputTotalPower`: Gendome devices use data
  point 165 and GO1000/GO2000 use data point 131. A value greater than zero
  means charging; charge-mode/status data points are not used.
- When both input/charge total power and output/discharge total power are zero,
  the device is in standby: both charging and discharging are false, while the
  dynamic remaining time still uses the discharge-side value.
- Product capabilities are inferred from semantic state keys until the backend
  adds an explicit capability object.

## License

MIT
