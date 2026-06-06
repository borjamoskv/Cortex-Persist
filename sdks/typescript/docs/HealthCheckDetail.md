
# HealthCheckDetail

Single health probe result.

## Properties

Name | Type
------------ | -------------
`status` | string
`detail` | string
`version` | string
`expected` | string
`actual` | string
`pendingUncheckpointed` | number
`lastCheckpointTx` | number
`activeConnections` | number
`maxConnections` | number
`utilization` | string
`usefulFactsRatio` | number
`duplicatesRatio` | number
`totalFacts` | number

## Example

```typescript
import type { HealthCheckDetail } from ''

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "detail": null,
  "version": null,
  "expected": null,
  "actual": null,
  "pendingUncheckpointed": null,
  "lastCheckpointTx": null,
  "activeConnections": null,
  "maxConnections": null,
  "utilization": null,
  "usefulFactsRatio": null,
  "duplicatesRatio": null,
  "totalFacts": null,
} satisfies HealthCheckDetail

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HealthCheckDetail
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


