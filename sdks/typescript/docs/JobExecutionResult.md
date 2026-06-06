
# JobExecutionResult


## Properties

Name | Type
------------ | -------------
`jobId` | string
`status` | string
`result` | { [key: string]: any; }
`proof` | string
`executedAt` | string

## Example

```typescript
import type { JobExecutionResult } from ''

// TODO: Update the object below with actual values
const example = {
  "jobId": null,
  "status": null,
  "result": null,
  "proof": null,
  "executedAt": null,
} satisfies JobExecutionResult

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as JobExecutionResult
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


