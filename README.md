# Radiopy

Radiopy is a set of Python scripts that fetches playlists from various radio stations and feeds them into Spotify playlists.
The project is still in its early stages and only supports a few radio stations.

## Setup

The easiest way to run the scripts is to use Docker. You can use the `docker-compose.yml` file to run the container.

```bash
docker-compose up -d  # Start the container in the background
docker-compose exec scheduler ./login.sh  # Login to Spotify
```
Make sure to restart the container after logging in to Spotify if the scheduler has already started a script.

By default, the script will add a new playlist for each radio station/channel and update the playlist every week.
You can change this behaviour by modifying the `cronfile` and adding a volume mapping to the `docker-compose.yml` file.

```yaml
    volumes:
      - ./cronfile:/app/cronfile  # use this if you want to use a custom cronfile
```

## Supported Radio Stations
- [bigFM](https://www.bigfm.de/) (uses [Regiocast](#regiocast) API)

## Upcoming Radio Stations

### [Antenne Bayern](https://www.antenne.de/)
#### Status: Found endpoint
- [Channel Metadata](https://www.antenne.de/api/channels)
- [Current Songs](https://www.antenne.de/api/metadata/now)

### [FFH](https://www.ffh.de/)
#### Status: Found endpoint
- [Current Songs](https://www.ffh.de/update-onair-info?tx_ffhonair_pi2[action]=getallsonginfo&tx_ffhonair_pi2[controller]=Webradio&tx_ffhonair_pi2[format]=json&type=210)

### [Regiocast](https://www.regiocast.de/)
#### Status: Still figuring out
- [search](https://asw.api.iris.radiorepo.io/v2/playlist/search.json?station=110&start=2024-11-20T20%3A53%3A55.631%2B01%3A00&end=2024-11-20T21%3A23%3A55.631%2B01%3A00)
- [flow/now](https://asw.api.iris.radiorepo.io/v2/playlist/flow.json?station=110&offset=1&count=1&ts=1716636546730)

Regiocast has many endpoints. Mostly radiorepo.io and loverad.io. Both have many subdomains.
It seems that the endpoint completely ignores timezones and uses the server's timezone. Probably Europe/Berlin.

#### Radio Stations
- [Radio Bob!](https://www.radiobob.de/)
- [Radio 7](https://www.radio7.de/)
- [bigFM](https://www.bigfm.de/)
- [Radio Regenbogen](https://www.regenbogen.de/)
- [Sunshine Live](https://www.sunshine-live.de/)
- ...


### [ARD](https://www.ardaudiothek.de/radio/)
#### Status: Prototype
- [GraphQL](https://api.ardaudiothek.de/graphql) (`permanentLivestream`)
- Current Songs: `https://programm-api.ard.de/radio/api/channel/{coreId}?pastHours=1`

ARD features many radio stations. The most popular ones are:
- [SWR3](https://www.swr3.de/)
- [Bayern 3](https://www.bayern3.de/) (covered by BR API)
- [HR3](https://www.hr3.de/)
- [MDR Jump](https://www.jumpradio.de/)
- [NDR 2](https://www.ndr.de/ndr2/)
- [WDR 2](https://www1.wdr.de/radio/wdr2/)
- [1Live](https://www1.wdr.de/radio/1live/)

### [BR](https://www.br.de/)
#### Status: Found endpoint
- [GraphQL](https://brradio.br.de/radio/v4)

The GraphQL endpoint seems to cover all data for all radio stations.