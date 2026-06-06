# LLMStatusResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Available** | **bool** |  | 
**Provider** | **string** |  | 
**Model** | Pointer to **NullableString** |  | [optional] 
**SupportedProviders** | **[]string** |  | 
**Providers** | Pointer to **[]map[string]interface{}** |  | [optional] 

## Methods

### NewLLMStatusResponse

`func NewLLMStatusResponse(available bool, provider string, supportedProviders []string, ) *LLMStatusResponse`

NewLLMStatusResponse instantiates a new LLMStatusResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewLLMStatusResponseWithDefaults

`func NewLLMStatusResponseWithDefaults() *LLMStatusResponse`

NewLLMStatusResponseWithDefaults instantiates a new LLMStatusResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAvailable

`func (o *LLMStatusResponse) GetAvailable() bool`

GetAvailable returns the Available field if non-nil, zero value otherwise.

### GetAvailableOk

`func (o *LLMStatusResponse) GetAvailableOk() (*bool, bool)`

GetAvailableOk returns a tuple with the Available field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAvailable

`func (o *LLMStatusResponse) SetAvailable(v bool)`

SetAvailable sets Available field to given value.


### GetProvider

`func (o *LLMStatusResponse) GetProvider() string`

GetProvider returns the Provider field if non-nil, zero value otherwise.

### GetProviderOk

`func (o *LLMStatusResponse) GetProviderOk() (*string, bool)`

GetProviderOk returns a tuple with the Provider field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProvider

`func (o *LLMStatusResponse) SetProvider(v string)`

SetProvider sets Provider field to given value.


### GetModel

`func (o *LLMStatusResponse) GetModel() string`

GetModel returns the Model field if non-nil, zero value otherwise.

### GetModelOk

`func (o *LLMStatusResponse) GetModelOk() (*string, bool)`

GetModelOk returns a tuple with the Model field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetModel

`func (o *LLMStatusResponse) SetModel(v string)`

SetModel sets Model field to given value.

### HasModel

`func (o *LLMStatusResponse) HasModel() bool`

HasModel returns a boolean if a field has been set.

### SetModelNil

`func (o *LLMStatusResponse) SetModelNil(b bool)`

 SetModelNil sets the value for Model to be an explicit nil

### UnsetModel
`func (o *LLMStatusResponse) UnsetModel()`

UnsetModel ensures that no value is present for Model, not even an explicit nil
### GetSupportedProviders

`func (o *LLMStatusResponse) GetSupportedProviders() []string`

GetSupportedProviders returns the SupportedProviders field if non-nil, zero value otherwise.

### GetSupportedProvidersOk

`func (o *LLMStatusResponse) GetSupportedProvidersOk() (*[]string, bool)`

GetSupportedProvidersOk returns a tuple with the SupportedProviders field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSupportedProviders

`func (o *LLMStatusResponse) SetSupportedProviders(v []string)`

SetSupportedProviders sets SupportedProviders field to given value.


### GetProviders

`func (o *LLMStatusResponse) GetProviders() []*map[string]interface{}`

GetProviders returns the Providers field if non-nil, zero value otherwise.

### GetProvidersOk

`func (o *LLMStatusResponse) GetProvidersOk() (*[]*map[string]interface{}, bool)`

GetProvidersOk returns a tuple with the Providers field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProviders

`func (o *LLMStatusResponse) SetProviders(v []*map[string]interface{})`

SetProviders sets Providers field to given value.

### HasProviders

`func (o *LLMStatusResponse) HasProviders() bool`

HasProviders returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


