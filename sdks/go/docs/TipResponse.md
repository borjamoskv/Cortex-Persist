# TipResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Id** | **string** |  | 
**Content** | **string** |  | 
**Category** | **string** |  | 
**Lang** | **string** |  | 
**Source** | **string** |  | 
**Project** | Pointer to **NullableString** |  | [optional] 
**Relevance** | Pointer to **float32** |  | [optional] [default to 1.0]
**Formatted** | Pointer to **string** |  | [optional] [default to ""]

## Methods

### NewTipResponse

`func NewTipResponse(id string, content string, category string, lang string, source string, ) *TipResponse`

NewTipResponse instantiates a new TipResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTipResponseWithDefaults

`func NewTipResponseWithDefaults() *TipResponse`

NewTipResponseWithDefaults instantiates a new TipResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetId

`func (o *TipResponse) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *TipResponse) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *TipResponse) SetId(v string)`

SetId sets Id field to given value.


### GetContent

`func (o *TipResponse) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *TipResponse) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *TipResponse) SetContent(v string)`

SetContent sets Content field to given value.


### GetCategory

`func (o *TipResponse) GetCategory() string`

GetCategory returns the Category field if non-nil, zero value otherwise.

### GetCategoryOk

`func (o *TipResponse) GetCategoryOk() (*string, bool)`

GetCategoryOk returns a tuple with the Category field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCategory

`func (o *TipResponse) SetCategory(v string)`

SetCategory sets Category field to given value.


### GetLang

`func (o *TipResponse) GetLang() string`

GetLang returns the Lang field if non-nil, zero value otherwise.

### GetLangOk

`func (o *TipResponse) GetLangOk() (*string, bool)`

GetLangOk returns a tuple with the Lang field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLang

`func (o *TipResponse) SetLang(v string)`

SetLang sets Lang field to given value.


### GetSource

`func (o *TipResponse) GetSource() string`

GetSource returns the Source field if non-nil, zero value otherwise.

### GetSourceOk

`func (o *TipResponse) GetSourceOk() (*string, bool)`

GetSourceOk returns a tuple with the Source field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSource

`func (o *TipResponse) SetSource(v string)`

SetSource sets Source field to given value.


### GetProject

`func (o *TipResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *TipResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *TipResponse) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *TipResponse) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *TipResponse) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *TipResponse) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetRelevance

`func (o *TipResponse) GetRelevance() float32`

GetRelevance returns the Relevance field if non-nil, zero value otherwise.

### GetRelevanceOk

`func (o *TipResponse) GetRelevanceOk() (*float32, bool)`

GetRelevanceOk returns a tuple with the Relevance field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRelevance

`func (o *TipResponse) SetRelevance(v float32)`

SetRelevance sets Relevance field to given value.

### HasRelevance

`func (o *TipResponse) HasRelevance() bool`

HasRelevance returns a boolean if a field has been set.

### GetFormatted

`func (o *TipResponse) GetFormatted() string`

GetFormatted returns the Formatted field if non-nil, zero value otherwise.

### GetFormattedOk

`func (o *TipResponse) GetFormattedOk() (*string, bool)`

GetFormattedOk returns a tuple with the Formatted field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFormatted

`func (o *TipResponse) SetFormatted(v string)`

SetFormatted sets Formatted field to given value.

### HasFormatted

`func (o *TipResponse) HasFormatted() bool`

HasFormatted returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


