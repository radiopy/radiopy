# Data Structure

## Redis

Data stored in the Redis database has a default expiration time of 2 weeks.
When this data expires, the associated playlist and link to that playlist are automatically deleted.

It's possible to add additional keys to the database (and to the JSON data), but this will be ignored as long as the
name doesn't interfere with the following keys. An example is `*:updated`, this is only for debugging purposes.

### `*:metadata`

Key Type: `string`
Used to identify playlists and categories.

```json
{
  "last_run": 1234567890,
  "type": "playlist",
  "name": "Your Radio Station",
  "description": "This is a description of the category/playlist",
  "url": "https://example.com",
  "image": "https://example.com/image.png",
  "reference": "some:redis:key",
  "invisible": true
}
```

| Key             | Type      | Required | Description                                                                                                   |
|-----------------|-----------|----------|---------------------------------------------------------------------------------------------------------------|
| `"last_run"`    | `integer` | yes      | UNIX timestamp                                                                                                |
| `"type"`        | `string`  | yes      | Either `"category"` or `"playlist"`                                                                           |
| `"name"`        | `string`  | yes      | Name                                                                                                          |
| `"description"` | `string`  | no       | Description                                                                                                   |
| `"url"`         | `string`  | no       | URL to a related website                                                                                      |
| `"image"`       | `string`  | no       | URL to a related image                                                                                        |
| `"reference"`   | `string`  | no       | Reference to another key in the Redis database. Inherits data from said key, but can be overwritten.          |
| `"invisible"`   | `bool`    | no       | If `true`, it won't show up in the overview. Default is `false`. Mostly used in combination with `reference`. |

### `*:songs`

Key Type: `list`
Used to add songs to the Spotify search queue.

```json
{
  "title": "Your Song",
  "artists": "Some Artist(s)",
  "id": "1651a3c486f3"
}
```

| Key         | Type     | Required | Description                                                                            |
|-------------|----------|----------|----------------------------------------------------------------------------------------|
| `"title"`   | `string` | yes      | Title of a song                                                                        |
| `"artists"` | `string` | no       | Artist(s) of a song                                                                    |
| `"id"`      | `string` | no       | ID of a song. Can be used if the radio station assigns IDs to songs. Used for caching. |

It's possible to add additional keys such as `"airtime"` or `"duration"`, but these are not processed in any way.
There are no plans to analyse this data. Yet.

### `cache:<SHA1 hash>`

Key Type: `string`
Used to cache search results from Spotify. The sha1 hash is retrieved by either using either the ID, if available, or
the search term.

```json
{
  "title": "Your Song",
  "artists": "Some Artist(s)",
  "id": "1651a3c486f3",
  "search_term": "track:Your Song artist:Some Artist(s)",
  "spotify_id": null
}
```

| Key             | Type            | required | Description                                                                                    |
|-----------------|-----------------|----------|------------------------------------------------------------------------------------------------|
| `"title"`       | `string`        | no       | Debugging only, no purpose                                                                     |
| `"artists"`     | `string`        | no       | Debugging only, no purpose                                                                     |
| `"id"`          | `string`        | no       | Debugging only, no purpose. The key of this item may be a SHA1 hash generated from this value. |
| `"search_term"` | `string`        | no       | Debugging only, no purpose. The key of this item may be a SHA1 hash generated from this value. |
| `"spotify_id"`  | `string`/`null` | yes      | Result from Spotify. It's just the base62 string. If null, then nothing was found.             |

### `*:queue`

Key Type: `list`
Results from the search queue. The value of an item is just a string with the Base62 Spotify ID.

### `mapping`

Key Type: `string`
Basically just a big dictionary that maps the Redis keys to their Spotify playlist.
The suffix `:metadata` is not included in the key.

```json
{
  "some:redis:key": "37i9dQZF1DXcBWIGoYBM5M",
  "...": "..."
}
```

### `token_info`

Key Type: `string`
Managed by the `spotipy` library.
> [!WARNING]
> This key contains sensitive data. Be sure to secure the database properly.
