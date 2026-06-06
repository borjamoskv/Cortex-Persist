
# StoreMemoryRequest


## Properties

Name | Type
------------ | -------------
`project` | string
`content` | string
`type` | string
`tags` | Array&lt;string&gt;
`source` | string
`metadata` | { [key: string]: any; }
`parentDecisionId` | number

## Example

```typescript
import type { StoreMemoryRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "project": null,
  "content": null,
  "type": null,
  "tags": null,
  "source": null,
  "metadata": null,
  "parentDecisionId": null,
} satisfies StoreMemoryRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as StoreMemoryRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


