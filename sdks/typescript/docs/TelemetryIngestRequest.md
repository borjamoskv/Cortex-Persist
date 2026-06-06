
# TelemetryIngestRequest


## Properties

Name | Type
------------ | -------------
`timestamp` | number
`agentId` | string
`payload` | [TelemetryPayload](TelemetryPayload.md)
`logosSignature` | string

## Example

```typescript
import type { TelemetryIngestRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "timestamp": null,
  "agentId": null,
  "payload": null,
  "logosSignature": null,
} satisfies TelemetryIngestRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TelemetryIngestRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


