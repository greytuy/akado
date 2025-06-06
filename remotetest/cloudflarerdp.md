End users can connect to an RDP server without the WARP client by authenticating through `cloudflared` in their native terminal. This method requires having `cloudflared` installed on both the server machine and on the client machine, as well as an active zone on Cloudflare. The traffic is proxied over this connection, and the user logs in to the server with their Cloudflare Access credentials.

Client-side `cloudflared` can be used in conjunction with [routing over WARP](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/use-cases/rdp/rdp-warp-to-tunnel/) and [Browser-based RDP](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/use-cases/rdp/rdp-browser/) so that there are multiple ways to connect to the server. You can reuse the same Cloudflare Tunnel when configuring each connection method.

## 1. Connect the server to Cloudflare

1. Create a Cloudflare Tunnel by following our [dashboard setup guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/).

2. In the **Public Hostnames** tab, choose a domain from the drop-down menu and specify any subdomain (for example, `rdp.example.com`).

3. For **Service**, select *RDP* and enter the [RDP listening port](https://docs.microsoft.com/en-us/windows-server/remote/remote-desktop-services/clients/change-listening-port) of your server (for example, `localhost:3389`). It will likely be port `3389`.

4. Select **Save hostname**.

## 2. (Recommended) Create an Access application

By default, anyone on the Internet can connect to the server using its public hostname. To allow or block specific users, create a [self-hosted application](https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/) in Cloudflare Access.

## 3. Connect as a user

1. [Install `cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) on the client machine.

2. Run this command to open an RDP listening port:

   ```sh
   cloudflared access rdp --hostname rdp.example.com --url rdp://localhost:3389
   ```

   This process will need to be configured to stay alive and autostart. If the process is killed, users will not be able to connect.

Note

If the client machine is running Windows, port `3389` may already be consumed locally. Select an alternative port to `3389` that is not being used.

1. While `cloudflared access` is running, connect from an RDP client such as Microsoft Remote Desktop:

   1. Open Microsoft Remote Desktop and select **Add a PC**.
   2. For **PC name**, enter `localhost:3389`.
   3. For **User account**, enter your RDP server username and password.
   4. Double-click the newly added PC.
   5. When asked if you want to continue, select **Continue**.

When the client launches, a browser window will open and prompt the user to authenticate with Cloudflare Access.
