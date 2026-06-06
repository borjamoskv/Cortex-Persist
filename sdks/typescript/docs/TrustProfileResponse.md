
# TrustProfileResponse


## Properties

Name | Type
------------ | -------------
`agentId` | string
`trustScore` | number
`successes` | number
`failures` | number
`taintEvents` | number
`lastSuccess` | string
`lastIncident` | string

## Example

```typescript
import type { TrustProfileResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "agentId": null,
  "trustScore": null,
  "successes": null,
  "failures": null,
  "taintEvents": null,
  "lastSuccess": null,
  "lastIncident": null,
} satisfies TrustProfileResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TrustProfileResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


