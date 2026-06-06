
# TranslateRequest


## Properties

Name | Type
------------ | -------------
`texts` | { [key: string]: string; }
`targetLanguages` | Array&lt;string&gt;
`context` | string

## Example

```typescript
import type { TranslateRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "texts": null,
  "targetLanguages": null,
  "context": null,
} satisfies TranslateRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TranslateRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


