# FRITZ!Box Tools

<a href="https://www.buymeacoffee.com/mammuth" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

Custom component for Home Assistant to control your FRITZ!Box

**Features:**

- Turn on/off guest wifi
- Reconnect your FRITZ!Box / get new IP from provider
- Manage port forwardings for your HomeAssistant device
- Sensor for internet connectivity (with external IP and uptime attributes)

![image](https://user-images.githubusercontent.com/3121306/64920971-d42cb000-d7bd-11e9-8bdf-a21c7ea93c58.png)


## Installation

**Install via HACS**

The custom component is available via [HACS](https://github.com/custom-components/hacs)

**Manual Install**

If you want to install the custom commponent manually, add the folder `fritzbox_tools/` to `YOUR_CONFIG_DIR/custom_components/`.

## Configuration

`configuration.yml`:
```yaml
fritzbox_tools:
  host: "192.168.178.1"
  username: "home-assistant"
  password: "yourfritzboxpassword"
  homeassistant_ip: "192.168.178.42"  # Optional. Needed if you want to control port forwardings for the device running HomeAssistant
```

**Port forwardings**

It's possible to enable/disable port forwardings for the device which is running HomeAssistant.

Requirements:
- Set the `homeassistant_ip` in the configuration of `fritzbox_tools`
- On your FRITZ!Box, enable the setting `Selbstständige Portfreigaben für dieses Gerät erlauben.` for the device which runs HA

The port forwards will be exposed as switches in your HA installation (search for `port_forward` in your entity page to find the IDs).

Note: **Currently only port forwards for the device which is running HA are supported!**

**Device profiles**

You can switch between two device profiles ("Zugangsprofile") within HomeAssistant for the devices within your network.

Requirements:
- Set `profile_on` and `profile_off` (default: "Gesperrt") in the configuration of `fritzbox_tools`
- On your FRITZ!Box, configure the profiles you want to be able to set for your devices.

The profile switches will be exposed as switches in your HA installation (search for `fritz_box_profile` in your entity page to find the IDs). If the switch is on `profile_on` is activated (or any other profile besides `profile_off`), if switch is off `profile_off` is activated.

Note: **due to the underlying library, the update routine is not the fastest. This might result in warnings**

## Examples
**Script: Reconnect / get new IP**

The following script can be used to easily add a reconnect button to your UI.

```yaml
fritz_box_reconnect:
  alias: "Reconnect FRITZ!Box"
  sequence:
  - service: fritzbox_tools.reconnect
```

**Automation: Reconnect / get new IP every night**

```yaml
automation:
- alias: "System: Reconnect FRITZ!Box"
  trigger:
    platform: time
    at: '05:00:00'
  action:
    - service: fritzbox_tools.reconnect
```

**Automation: Phone notification with wifi credentials when guest wifi is created**

The custom component registers a switch for controlling the guest wifi and a service for triggering a reconnect. I use the following automation to send the guest wifi password to my wife's and my phones whenever we turn on the guest wifi:
```yaml
automation:
  - alias: "Guests Wifi Turned On -> Send Password To Phone
    trigger:
      platform: state
      entity_id: switch.fritz_box_guest_wifi
      to: 'on'
    action:
      - service: notify.pushbullet_max
        data:
          title: "Guest wifi is enabled"
          message: "Password: ..."
```


## Exposed entities

- `service.reconnect`  Reconnect to your ISP
- `switch.fritz_box_guest_wifi`  Turns on/off guest wifi
- `sensor.fritz_box_connectivity`  online/offline depending on your internet connection
- `switch.port_forward_[description of your forward]` for each of your port forwards for your HA device
- `switch.fritz_box_profile_[name of your device]` for each device in your fritzbox network


## Contributors

- [@mammuth](http://github.com/mammuth)
- [@AaronDavidSchneider](http://github.com/AaronDavidSchneider)
- [@jo-me](http://github.com/jo-me)
