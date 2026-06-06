
# HeartbeatRequest


## Properties

Name | Type
------------ | -------------
`project` | string
`entity` | string
`category` | string
`branch` | string
`language` | string
`meta` | { [key: string]: any; }

## Example

```typescript
import type { HeartbeatRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "project": null,
  "entity": null,
  "category": null,
  "branch": null,
  "language": null,
  "meta": null,
} satisfies HeartbeatRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HeartbeatRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


