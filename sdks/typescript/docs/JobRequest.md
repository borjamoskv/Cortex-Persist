
# JobRequest


## Properties

Name | Type
------------ | -------------
`taskType` | string
`payload` | { [key: string]: any; }
`sla` | [JobSLA](JobSLA.md)

## Example

```typescript
import type { JobRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "taskType": null,
  "payload": null,
  "sla": null,
} satisfies JobRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as JobRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


