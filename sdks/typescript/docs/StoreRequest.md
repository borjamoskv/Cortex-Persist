
# StoreRequest


## Properties

Name | Type
------------ | -------------
`project` | string
`content` | string
`factType` | string
`tags` | Array&lt;string&gt;
`source` | string
`confidence` | string
`meta` | { [key: string]: any; }

## Example

```typescript
import type { StoreRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "project": null,
  "content": null,
  "factType": null,
  "tags": null,
  "source": null,
  "confidence": null,
  "meta": null,
} satisfies StoreRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as StoreRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


