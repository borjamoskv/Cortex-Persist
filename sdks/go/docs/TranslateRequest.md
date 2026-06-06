# TranslateRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Texts** | **map[string]string** | Dictionary of key-value pairs to translate. Max 100 items. | 
**TargetLanguages** | **[]string** | List of target language codes (e.g., [&#39;es&#39;, &#39;fr&#39;, &#39;zh&#39;]). | 
**Context** | Pointer to **NullableString** | Optional context about the application or tone. | [optional] 

## Methods

### NewTranslateRequest

`func NewTranslateRequest(texts map[string]string, targetLanguages []string, ) *TranslateRequest`

NewTranslateRequest instantiates a new TranslateRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTranslateRequestWithDefaults

`func NewTranslateRequestWithDefaults() *TranslateRequest`

NewTranslateRequestWithDefaults instantiates a new TranslateRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTexts

`func (o *TranslateRequest) GetTexts() map[string]string`

GetTexts returns the Texts field if non-nil, zero value otherwise.

### GetTextsOk

`func (o *TranslateRequest) GetTextsOk() (*map[string]string, bool)`

GetTextsOk returns a tuple with the Texts field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTexts

`func (o *TranslateRequest) SetTexts(v map[string]string)`

SetTexts sets Texts field to given value.


### GetTargetLanguages

`func (o *TranslateRequest) GetTargetLanguages() []string`

GetTargetLanguages returns the TargetLanguages field if non-nil, zero value otherwise.

### GetTargetLanguagesOk

`func (o *TranslateRequest) GetTargetLanguagesOk() (*[]string, bool)`

GetTargetLanguagesOk returns a tuple with the TargetLanguages field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTargetLanguages

`func (o *TranslateRequest) SetTargetLanguages(v []string)`

SetTargetLanguages sets TargetLanguages field to given value.


### GetContext

`func (o *TranslateRequest) GetContext() string`

GetContext returns the Context field if non-nil, zero value otherwise.

### GetContextOk

`func (o *TranslateRequest) GetContextOk() (*string, bool)`

GetContextOk returns a tuple with the Context field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContext

`func (o *TranslateRequest) SetContext(v string)`

SetContext sets Context field to given value.

### HasContext

`func (o *TranslateRequest) HasContext() bool`

HasContext returns a boolean if a field has been set.

### SetContextNil

`func (o *TranslateRequest) SetContextNil(b bool)`

 SetContextNil sets the value for Context to be an explicit nil

### UnsetContext
`func (o *TranslateRequest) UnsetContext()`

UnsetContext ensures that no value is present for Context, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


