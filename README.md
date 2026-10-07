# Anubis Configuration Support

**This is still experimental, use at your own risk**

Anubis is an open source project which attempts to block web scrapers. It behaves as a reverse proxy, deciding whether to forward on requests to the service being protected or block them. EPrints is susceptible to being taken offline by swarms of AI bots which are indistinguishable from a DDOS attack. The CPU heavy search and statistics pages can very easily be overwhelmed and take an entire repository offline.

The default configuration aims to reach a balance between being as open as possible - we should like to allow well behaved scrapers to index EPrints - but blocking the worst bots to prioritise staying online.

Multiple repositories on the same host (with their own virtualhosts) is supported.

## TODO List
 - Error message from generate_apacheconf_for_anubis or support for HTTP (no ssl) or HTTP & HTTPs with no HTTP->HTTPS redirect.

## How to configure

1. Ensure EPrints is currently configured to use SSL in the standard way [as per the wiki](https://wiki.eprints.org/w/How_to_use_EPrints_with_HTTPS) with the SSL configuration in archive/*/ssl/securevhost.conf
2. Install Anubis. [Anubis official install guide](https://anubis.techaro.lol/docs/admin/native-install/). Official deb and RPM files are available.
3. Install this ingredient: 
   1. `cd /opt/eprints3/ingredients`
   2. `git clone https://github.com/eprints/anubis.git`
   3. `git checkout v0.6` (or whichever release your desire)
   4. `echo "ingredients/anubis" >> /opt/eprints3/flavours/pub_lib/inc`
4. Copy `/opt/eprints3/ingredients/anubis/anubis_config/eprints.botPolicies.yaml` to `/opt/eprints3/archives/[YOUR ARCHIVE ID]/anubis/eprints.botPolicies.yaml`
   - Alternatively use `eprints_permissive.botPolicies.yaml` which only blocks known bad bots and otherwise won't do any proof of work
5. Create `/etc/anubis/eprints.env` with: 
```BIND=:8923
DIFFICULTY=4
METRICS_BIND=[::1]:9090
METRICS_BIND_NETWORK=tcp
SERVE_ROBOTS_TXT=0
TARGET=http://[::1]:3000
POLICY_FNAME=/opt/eprints3/archives/[YOUR ARCHIVE ID]/anubis/eprints.botPolicies.yaml
```
6. Enable and start systemd module for anubis for EPrints: `sudo systemctl enable --now anubis@eprints.service`. Do not proceed further until the anubis service is running!
7. Run `/opt/eprints3/ingredients/anubis/bin/generate_apacheconf_for_anubis` to update EPrints apache config files to set up the Anubis proxy
8. Confirm `/opt/eprints3/archives/[YOUR ARCHIVE ID]/ssl/securevhost.conf` is correct. In most circumstances it shouldn't need editing:
   1.  It should already `Include /opt/eprints3/cfg/apache_ssl/[YOUR ARCHIVE ID].conf` which is now the anubis configuration rather than EPrints.
   2.  Note that if you have any SSL aliases, you may have to re-configure the SSL redirects yourself in this file.
   3.  An example SSL config file using Lets Encrypt is provided in `/opt/eprints3/ingredients/anubis/ssl/securevhost.conf.example` for reference. 
9.  Restart apache: `sudo systemctl restart httpd` 

If you need to revert the apache config changes use `/opt/eprints3/ingredients/anubis/bin/generate_apacheconf_for_anubis --undo`

Note that I recommend disabling any rate-limiting that mod_security may be performing as I'm not sure how this interacts with Anubis.

## Rate Limiting and Caching With Nginx

Even with Anubis configured some repositories have still experienced extremely heavy CPU load and been taken offline. An experimental rate and connection limiting and caching config for nginx is available. This enables a cache for non-logged in users accessing CPU heavy pages, and also limits for requests per IP and overall.

The caching should be able to make a significant improvement in response times when under heavy load from some of the stranger bot swarms which make thousands of identical requests. In order to support caching, some minor changes are required to how EPrints uses cookies to store login sessions. The fixes are contained in z_fix_cookies.pl.disabled and this should be copied into the archive and enabled (remove .disabled from name) until this is fixed in EPrints core - hopefully in EPrints 3.4.8.

Nginx listens on port 4000, behind Anubis and in front of EPrints. It will limit rates globally and per-IP and limit the maximum number of simultanious connections to CPU heavy pages (configurable). When limits have been reached, an HTTP 503 is sent, with a page explaining which feature is temporarily offline. This should keep a lid on the maximum CPU usage and enable EPrints to stay alive, even if search, stats, and export functionality stops working.  The default configuration is intended to allow all connections through under normal load, and start blocking connections (responding with a page saying "[repo name] is under heavy load and [feature] is temporarily unavailable. Please try again later.") only when necessary to keep the server online and responding in a timely manner to other requests.

Run `/opt/eprints3/ingredients/anubis/bin/generate_apacheconf_for_anubis --ratelimit` to configure Apache to forward to nginx and override the default HTTP 503 behaviour.

Copy `/opt/eprints3/ingredients/anubis/rate_limiting/eprints_nginx_rate_limiting.conf` to `/opt/eprints/archives/[ARCHIVE ID]/nginx/eprints_nginx_rate_limiting.conf` where you can make archive specific changes. Then make sure that this is included in nginx. On Red Hat you will want to remove the `server {}` block in `/etc/nginx/nginx.conf` and create `/etc/nginx/conf.d/eprints.conf` with the content:

```
include /opt/eprints3/archives/[YOUR ARCHIVE ID]/nginx/*.conf;
```

On most other distros you will want to remove `/etc/nginx/sites_enabled/default` and create `/etc/nginx/sites_enabled/eprints.conf` with the above content instead.


## Diagrams

### With Rate Limiting using Nginx
```mermaid
flowchart LR
   
   TCP(Apache:80/443\nsecurevhosts.conf)
   EPR(Apache for EPrints:3000\ncfg/apache/ARCHIVE.conf)
   

   subgraph Filtering and Rate Limiting
      ANU(Anubis:9090)
      PROOF(Proof of Work)
      BAD(Bad Bot Rules Only)
      RATE(Rate & Connection Limiting)
      NGX(Nginx:4000 \neprints_nginx_rate_limiting.conf)
      
   end

   
   TCP -->  ANU
   ANU --> | CPU Heavy Pages | PROOF
   PROOF -.-> NGX
   ANU --> | All Other Pages | BAD
   BAD -.-> NGX
   NGX --> | CPU Heavy Pages | RATE
   
   RATE -.->  EPR
   NGX --> | All Other Pages | EPR
   
```

### Without Rate Limiting
```mermaid
flowchart LR
   
   TCP(Apache:80/443\nsecurevhosts.conf)
   EPR(Apache for EPrints:3000\ncfg/apache/ARCHIVE.conf)
   

   subgraph Filtering
      ANU(Anubis:9090)
      PROOF(Proof of Work)
      BAD(Bad Bot Rules Only)
   end

   
   TCP -->  ANU
   ANU --> | CPU Heavy Pages | PROOF
   PROOF -.-> EPR
   ANU --> | All Other Pages | BAD
   BAD -.-> EPR
   
```

## How to confirm this is working

Open a new browser, or an incogneto window in a browser and navigate to your repository's search page. When first loading the search page you should briefly see the anubis logo pop up.

Log in as an administrator and navigate to the Admin page. Under "System Tools" there should be a new button "Anubis Status". This page will report Anubis' metrics. Note that the metrics are the current cumulative total. Future work could including some way of logging and graphing these metrics to keep an eye on Anubis.

## How to unconfigure

If anything has gone wrong, or for whatever reason you need to remove anubis, you can run:
`/opt/eprints3/ingredients/anubis/bin/generate_apacheconf_for_anubis --undo`

This will put EPrints' Apache config back to how it was before. Anubis will still be running as a service in the background, but Apache will not be routing any traffic through it.

## SELinux

If the Anubis Status page in EPrints shows a permission denied error, it is likely SELinux blocking apache/EPrints from making a request to Anubis' metrics.

The following (as root) can fix this by adding in a rule:

Create `anubismetrics.te` with the contents:

```

module anubismetrics 1.0;

require {
        type mysqld_tmp_t;
        type websm_port_t;
        type port_t;
        type mysqld_port_t;
        type httpd_t;
        type init_t;
        class file unlink;
        class tcp_socket name_connect;
}


#============= httpd_t ==============

#!!!! This avc can be allowed using one of the these booleans:
#     httpd_can_network_connect, httpd_can_network_connect_db
allow httpd_t mysqld_port_t:tcp_socket name_connect;

#!!!! This avc can be allowed using one of the these booleans:
#     httpd_can_network_connect, nis_enabled
allow httpd_t port_t:tcp_socket name_connect;

#!!!! This avc can be allowed using the boolean 'httpd_can_network_connect'
allow httpd_t websm_port_t:tcp_socket name_connect;

```

Create `anubismetrics.mod` with:
`checkmodule -M -m -o anubismetrics.mod anubismetrics.te`

Create `anubismetrics.pp` file with:
`semodule_package -o anubismetrics.pp -m anubismetrics.mod`

Install this rule with:
`semodule -i anubismetrics.pp`

For more help generating SELinux rules [the redhat docs](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/6/html/security-enhanced_linux/sect-security-enhanced_linux-fixing_problems-allowing_access_audit2allow) are very useful.

## Common Custom Anubis Rules

In `/opt/eprints3/archives/[YOUR ARCHIVE ID]/anubis/eprints.botPolicies.yaml` the default Anubis bot list is used and a proof-of-work check is enabled only for stats and search. Export may also need to be covered, we are still experimenting with the best policy.

# IP Whitelist

The remote_addresses argument expects CIDR notation, for a single IP use "/32".

```
- name: ip-whitelist
    action: ALLOW
    remote_addresses:
      [
        "152.78.x.x/32"
      ]
```
