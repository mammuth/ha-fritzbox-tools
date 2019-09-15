# FRITZ!Box Tools
Custom component for Home Assistant to control your FRITZ!Box

**Features:**

- Turn on/off guest wifi
- Reconnect your FRITZ!Box / get new IP from provider

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
```

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
