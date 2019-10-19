# FRITZ!Box Tools

This custom component allows you to get more out of your FRITZ!Box


**Features:**

- Switch between device profiles ("Zugangsprofile") for devices in your network
- Manage port forwardings for your Home Assistant device
- Turn on/off guest wifi
- Reconnect your FRITZ!Box / get new IP from provider
- Sensor for internet connectivity (with external IP and uptime attributes)

![image](https://user-images.githubusercontent.com/3121306/67151935-01451480-f2ce-11e9-8f32-473b412935c9.png)


**Configuration (minimal):**

`configuration.yml`:
```yaml
fritzbox_tools:
  host: "192.168.178.1"
  username: "home-assistant"  # Skip if you don't have a user
  password: "yourfritzboxpassword"
```

Check out the [README](https://github.com/mammuth/ha-fritzbox-tools/blob/master/README.md#configuration) for a detailed documentation on how to configure this custom component

<a href="https://www.buymeacoffee.com/mammuth" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>
