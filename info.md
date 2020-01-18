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

***As Integration (recommended):***

Go to the `Integrations pane` on your Home Assistant instance and add `FRITZ!Box Tools`.

***Via `configuration.yml`:***
```yaml
fritzbox_tools:
  host: "192.168.178.1"
  username: "home-assistant"  # create one at `System > FRITZ!Box Benutzer` on your router
  password: "yourfritzboxpassword"
```

Check out the [README](https://github.com/mammuth/ha-fritzbox-tools/blob/master/README.md#configuration) for a detailed documentation on how to configure this custom component


#### Prepare your FRITZ!Box

If you want to be able to control settings of the FRITZ!Box (eg. toggle device profiles, guest wifi, port forwards, ...), you need to enable two settings in the FRITZ!Box UI `Home > Network > Network Settings (Tab)` as seen in the following screenshot:

![network-settings](https://user-images.githubusercontent.com/3121306/68996105-e5fe0280-0895-11ea-8b0d-1a4487ee6838.png)


<a href="https://www.buymeacoffee.com/mammuth" target="_blank"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>
