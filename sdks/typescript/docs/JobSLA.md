
# JobSLA


## Properties

Name | Type
------------ | -------------
`confidenceLevel` | string
`maxLatencyMs` | number
`requiresZkProof` | boolean

## Example

```typescript
import type { JobSLA } from ''

// TODO: Update the object below with actual values
const example = {
  "confidenceLevel": null,
  "maxLatencyMs": null,
  "requiresZkProof": null,
} satisfies JobSLA

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as JobSLA
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


