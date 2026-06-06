# TipsListResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Tips** | [**[]TipResponse**](TipResponse.md) |  | 
**Count** | **int32** | Number of tips returned | 
**Lang** | **string** |  | 
**Category** | Pointer to **NullableString** |  | [optional] 
**Project** | Pointer to **NullableString** |  | [optional] 
**TotalAvailable** | Pointer to **NullableInt32** |  | [optional] 

## Methods

### NewTipsListResponse

`func NewTipsListResponse(tips []TipResponse, count int32, lang string, ) *TipsListResponse`

NewTipsListResponse instantiates a new TipsListResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTipsListResponseWithDefaults

`func NewTipsListResponseWithDefaults() *TipsListResponse`

NewTipsListResponseWithDefaults instantiates a new TipsListResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTips

`func (o *TipsListResponse) GetTips() []TipResponse`

GetTips returns the Tips field if non-nil, zero value otherwise.

### GetTipsOk

`func (o *TipsListResponse) GetTipsOk() (*[]TipResponse, bool)`

GetTipsOk returns a tuple with the Tips field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTips

`func (o *TipsListResponse) SetTips(v []TipResponse)`

SetTips sets Tips field to given value.


### GetCount

`func (o *TipsListResponse) GetCount() int32`

GetCount returns the Count field if non-nil, zero value otherwise.

### GetCountOk

`func (o *TipsListResponse) GetCountOk() (*int32, bool)`

GetCountOk returns a tuple with the Count field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCount

`func (o *TipsListResponse) SetCount(v int32)`

SetCount sets Count field to given value.


### GetLang

`func (o *TipsListResponse) GetLang() string`

GetLang returns the Lang field if non-nil, zero value otherwise.

### GetLangOk

`func (o *TipsListResponse) GetLangOk() (*string, bool)`

GetLangOk returns a tuple with the Lang field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLang

`func (o *TipsListResponse) SetLang(v string)`

SetLang sets Lang field to given value.


### GetCategory

`func (o *TipsListResponse) GetCategory() string`

GetCategory returns the Category field if non-nil, zero value otherwise.

### GetCategoryOk

`func (o *TipsListResponse) GetCategoryOk() (*string, bool)`

GetCategoryOk returns a tuple with the Category field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCategory

`func (o *TipsListResponse) SetCategory(v string)`

SetCategory sets Category field to given value.

### HasCategory

`func (o *TipsListResponse) HasCategory() bool`

HasCategory returns a boolean if a field has been set.

### SetCategoryNil

`func (o *TipsListResponse) SetCategoryNil(b bool)`

 SetCategoryNil sets the value for Category to be an explicit nil

### UnsetCategory
`func (o *TipsListResponse) UnsetCategory()`

UnsetCategory ensures that no value is present for Category, not even an explicit nil
### GetProject

`func (o *TipsListResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *TipsListResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *TipsListResponse) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *TipsListResponse) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *TipsListResponse) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *TipsListResponse) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetTotalAvailable

`func (o *TipsListResponse) GetTotalAvailable() int32`

GetTotalAvailable returns the TotalAvailable field if non-nil, zero value otherwise.

### GetTotalAvailableOk

`func (o *TipsListResponse) GetTotalAvailableOk() (*int32, bool)`

GetTotalAvailableOk returns a tuple with the TotalAvailable field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalAvailable

`func (o *TipsListResponse) SetTotalAvailable(v int32)`

SetTotalAvailable sets TotalAvailable field to given value.

### HasTotalAvailable

`func (o *TipsListResponse) HasTotalAvailable() bool`

HasTotalAvailable returns a boolean if a field has been set.

### SetTotalAvailableNil

`func (o *TipsListResponse) SetTotalAvailableNil(b bool)`

 SetTotalAvailableNil sets the value for TotalAvailable to be an explicit nil

### UnsetTotalAvailable
`func (o *TipsListResponse) UnsetTotalAvailable()`

UnsetTotalAvailable ensures that no value is present for TotalAvailable, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


