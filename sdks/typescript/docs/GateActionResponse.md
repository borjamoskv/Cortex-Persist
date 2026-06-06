
# GateActionResponse


## Properties

Name | Type
------------ | -------------
`actionId` | string
`level` | string
`description` | string
`command` | Array&lt;string&gt;
`project` | string
`status` | string
`createdAt` | string
`approvedAt` | string
`operatorId` | string

## Example

```typescript
import type { GateActionResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "actionId": null,
  "level": null,
  "description": null,
  "command": null,
  "project": null,
  "status": null,
  "createdAt": null,
  "approvedAt": null,
  "operatorId": null,
} satisfies GateActionResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GateActionResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


