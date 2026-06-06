
# DeepHealthResponse

Structured deep health check response.

## Properties

Name | Type
------------ | -------------
`status` | string
`version` | string
`schemaVersion` | string
`checks` | [{ [key: string]: HealthCheckDetail; }](HealthCheckDetail.md)
`latencyMs` | number
`p95LatencyMs` | number
`staleRatio` | number

## Example

```typescript
import type { DeepHealthResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "version": null,
  "schemaVersion": null,
  "checks": null,
  "latencyMs": null,
  "p95LatencyMs": null,
  "staleRatio": null,
} satisfies DeepHealthResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DeepHealthResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


