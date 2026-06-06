
# TimeSummaryResponse


## Properties

Name | Type
------------ | -------------
`totalSeconds` | number
`totalHours` | number
`byCategory` | { [key: string]: number; }
`byProject` | { [key: string]: number; }
`entries` | number
`heartbeats` | number
`topEntities` | Array&lt;Array&lt;any&gt;&gt;

## Example

```typescript
import type { TimeSummaryResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "totalSeconds": null,
  "totalHours": null,
  "byCategory": null,
  "byProject": null,
  "entries": null,
  "heartbeats": null,
  "topEntities": null,
} satisfies TimeSummaryResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TimeSummaryResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


