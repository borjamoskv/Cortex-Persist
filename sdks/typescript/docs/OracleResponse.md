
# OracleResponse

The Oracle\'s audit report.

## Properties

Name | Type
------------ | -------------
`target` | string
`agent` | string
`report` | string
`confidence` | number
`status` | string

## Example

```typescript
import type { OracleResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "target": null,
  "agent": null,
  "report": null,
  "confidence": null,
  "status": null,
} satisfies OracleResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as OracleResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


