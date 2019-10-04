# FRITZ!Box Tools

This custom component allows you to get more out of your FRITZ!Box


**Features:**

- Turn on/off guest wifi
- Reconnect your FRITZ!Box / get new IP from provider
- Manage port forwardings for your HomeAssistant device
- Switch between device profiles ("Zugangsprofile") for devices in your network
- Sensor for internet connectivity (with external IP and uptime attributes)


![image](https://user-images.githubusercontent.com/3121306/64920971-d42cb000-d7bd-11e9-8bdf-a21c7ea93c58.png)

**Configuration:**

`configuration.yml`:
```yaml
fritzbox_tools:
  host: "192.168.178.1"
  username: "home-assistant"
  password: "yourfritzboxpassword"
  homeassistant_ip: "192.168.178.42"  # Optional. Needed if you want to control port forwardings for the device running HomeAssistant
  profile_on: "Standard"  # Optional. Needed if you want to switch between device profiles ("Zugangsprofile")
  profile_off: "Gesperrt"  # Optional. Needed if you want to switch between device profiles ("Zugangsprofile")
  device_list: # Optional. If you don't want to expose a profile switch for just some of your network devices
    - "Helens-iPhone"
    - "Aarons-MacBook-Air"
    - "..."
```


<a href="https://www.buymeacoffee.com/mammuth" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>
