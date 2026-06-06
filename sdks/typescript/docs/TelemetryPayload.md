
# TelemetryPayload


## Properties

Name | Type
------------ | -------------
`telemetryLogs` | Array&lt;{ [key: string]: any; } | null&gt;
`newEdges` | { [key: string]: number; }
`authorsDelta` | { [key: string]: { [key: string]: any; } | null; }

## Example

```typescript
import type { TelemetryPayload } from ''

// TODO: Update the object below with actual values
const example = {
  "telemetryLogs": null,
  "newEdges": null,
  "authorsDelta": null,
} satisfies TelemetryPayload

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TelemetryPayload
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


