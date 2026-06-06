# TranslateResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Translations** | **map[string]map[string]string** | A dictionary mapping language codes to their translated key-value pairs. | 
**Usage** | Pointer to **map[string]int32** |  | [optional] 

## Methods

### NewTranslateResponse

`func NewTranslateResponse(translations map[string]map[string]string, ) *TranslateResponse`

NewTranslateResponse instantiates a new TranslateResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTranslateResponseWithDefaults

`func NewTranslateResponseWithDefaults() *TranslateResponse`

NewTranslateResponseWithDefaults instantiates a new TranslateResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTranslations

`func (o *TranslateResponse) GetTranslations() map[string]map[string]string`

GetTranslations returns the Translations field if non-nil, zero value otherwise.

### GetTranslationsOk

`func (o *TranslateResponse) GetTranslationsOk() (*map[string]map[string]string, bool)`

GetTranslationsOk returns a tuple with the Translations field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTranslations

`func (o *TranslateResponse) SetTranslations(v map[string]map[string]string)`

SetTranslations sets Translations field to given value.


### GetUsage

`func (o *TranslateResponse) GetUsage() map[string]int32`

GetUsage returns the Usage field if non-nil, zero value otherwise.

### GetUsageOk

`func (o *TranslateResponse) GetUsageOk() (*map[string]int32, bool)`

GetUsageOk returns a tuple with the Usage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUsage

`func (o *TranslateResponse) SetUsage(v map[string]int32)`

SetUsage sets Usage field to given value.

### HasUsage

`func (o *TranslateResponse) HasUsage() bool`

HasUsage returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


