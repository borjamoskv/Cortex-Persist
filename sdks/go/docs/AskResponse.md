# AskResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Answer** | **string** |  | 
**Sources** | [**[]AskSource**](AskSource.md) |  | 
**Model** | **string** |  | 
**Provider** | **string** |  | 
**FactsFound** | **int32** |  | 

## Methods

### NewAskResponse

`func NewAskResponse(answer string, sources []AskSource, model string, provider string, factsFound int32, ) *AskResponse`

NewAskResponse instantiates a new AskResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAskResponseWithDefaults

`func NewAskResponseWithDefaults() *AskResponse`

NewAskResponseWithDefaults instantiates a new AskResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAnswer

`func (o *AskResponse) GetAnswer() string`

GetAnswer returns the Answer field if non-nil, zero value otherwise.

### GetAnswerOk

`func (o *AskResponse) GetAnswerOk() (*string, bool)`

GetAnswerOk returns a tuple with the Answer field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAnswer

`func (o *AskResponse) SetAnswer(v string)`

SetAnswer sets Answer field to given value.


### GetSources

`func (o *AskResponse) GetSources() []AskSource`

GetSources returns the Sources field if non-nil, zero value otherwise.

### GetSourcesOk

`func (o *AskResponse) GetSourcesOk() (*[]AskSource, bool)`

GetSourcesOk returns a tuple with the Sources field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSources

`func (o *AskResponse) SetSources(v []AskSource)`

SetSources sets Sources field to given value.


### GetModel

`func (o *AskResponse) GetModel() string`

GetModel returns the Model field if non-nil, zero value otherwise.

### GetModelOk

`func (o *AskResponse) GetModelOk() (*string, bool)`

GetModelOk returns a tuple with the Model field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetModel

`func (o *AskResponse) SetModel(v string)`

SetModel sets Model field to given value.


### GetProvider

`func (o *AskResponse) GetProvider() string`

GetProvider returns the Provider field if non-nil, zero value otherwise.

### GetProviderOk

`func (o *AskResponse) GetProviderOk() (*string, bool)`

GetProviderOk returns a tuple with the Provider field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProvider

`func (o *AskResponse) SetProvider(v string)`

SetProvider sets Provider field to given value.


### GetFactsFound

`func (o *AskResponse) GetFactsFound() int32`

GetFactsFound returns the FactsFound field if non-nil, zero value otherwise.

### GetFactsFoundOk

`func (o *AskResponse) GetFactsFoundOk() (*int32, bool)`

GetFactsFoundOk returns a tuple with the FactsFound field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactsFound

`func (o *AskResponse) SetFactsFound(v int32)`

SetFactsFound sets FactsFound field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


