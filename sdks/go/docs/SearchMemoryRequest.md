# SearchMemoryRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Query** | **string** |  | 
**K** | Pointer to **int32** |  | [optional] [default to 5]
**Project** | Pointer to **NullableString** |  | [optional] 
**Tags** | Pointer to **[]string** |  | [optional] 
**AsOf** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewSearchMemoryRequest

`func NewSearchMemoryRequest(query string, ) *SearchMemoryRequest`

NewSearchMemoryRequest instantiates a new SearchMemoryRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSearchMemoryRequestWithDefaults

`func NewSearchMemoryRequestWithDefaults() *SearchMemoryRequest`

NewSearchMemoryRequestWithDefaults instantiates a new SearchMemoryRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetQuery

`func (o *SearchMemoryRequest) GetQuery() string`

GetQuery returns the Query field if non-nil, zero value otherwise.

### GetQueryOk

`func (o *SearchMemoryRequest) GetQueryOk() (*string, bool)`

GetQueryOk returns a tuple with the Query field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetQuery

`func (o *SearchMemoryRequest) SetQuery(v string)`

SetQuery sets Query field to given value.


### GetK

`func (o *SearchMemoryRequest) GetK() int32`

GetK returns the K field if non-nil, zero value otherwise.

### GetKOk

`func (o *SearchMemoryRequest) GetKOk() (*int32, bool)`

GetKOk returns a tuple with the K field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetK

`func (o *SearchMemoryRequest) SetK(v int32)`

SetK sets K field to given value.

### HasK

`func (o *SearchMemoryRequest) HasK() bool`

HasK returns a boolean if a field has been set.

### GetProject

`func (o *SearchMemoryRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *SearchMemoryRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *SearchMemoryRequest) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *SearchMemoryRequest) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *SearchMemoryRequest) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *SearchMemoryRequest) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetTags

`func (o *SearchMemoryRequest) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *SearchMemoryRequest) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *SearchMemoryRequest) SetTags(v []string)`

SetTags sets Tags field to given value.

### HasTags

`func (o *SearchMemoryRequest) HasTags() bool`

HasTags returns a boolean if a field has been set.

### SetTagsNil

`func (o *SearchMemoryRequest) SetTagsNil(b bool)`

 SetTagsNil sets the value for Tags to be an explicit nil

### UnsetTags
`func (o *SearchMemoryRequest) UnsetTags()`

UnsetTags ensures that no value is present for Tags, not even an explicit nil
### GetAsOf

`func (o *SearchMemoryRequest) GetAsOf() string`

GetAsOf returns the AsOf field if non-nil, zero value otherwise.

### GetAsOfOk

`func (o *SearchMemoryRequest) GetAsOfOk() (*string, bool)`

GetAsOfOk returns a tuple with the AsOf field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAsOf

`func (o *SearchMemoryRequest) SetAsOf(v string)`

SetAsOf sets AsOf field to given value.

### HasAsOf

`func (o *SearchMemoryRequest) HasAsOf() bool`

HasAsOf returns a boolean if a field has been set.

### SetAsOfNil

`func (o *SearchMemoryRequest) SetAsOfNil(b bool)`

 SetAsOfNil sets the value for AsOf to be an explicit nil

### UnsetAsOf
`func (o *SearchMemoryRequest) UnsetAsOf()`

UnsetAsOf ensures that no value is present for AsOf, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


