# OracleRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**TargetUrl** | **string** |  | 
**AgentType** | Pointer to **string** |  | [optional] [default to "ariadne"]
**Depth** | Pointer to **int32** |  | [optional] [default to 1]

## Methods

### NewOracleRequest

`func NewOracleRequest(targetUrl string, ) *OracleRequest`

NewOracleRequest instantiates a new OracleRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewOracleRequestWithDefaults

`func NewOracleRequestWithDefaults() *OracleRequest`

NewOracleRequestWithDefaults instantiates a new OracleRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTargetUrl

`func (o *OracleRequest) GetTargetUrl() string`

GetTargetUrl returns the TargetUrl field if non-nil, zero value otherwise.

### GetTargetUrlOk

`func (o *OracleRequest) GetTargetUrlOk() (*string, bool)`

GetTargetUrlOk returns a tuple with the TargetUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTargetUrl

`func (o *OracleRequest) SetTargetUrl(v string)`

SetTargetUrl sets TargetUrl field to given value.


### GetAgentType

`func (o *OracleRequest) GetAgentType() string`

GetAgentType returns the AgentType field if non-nil, zero value otherwise.

### GetAgentTypeOk

`func (o *OracleRequest) GetAgentTypeOk() (*string, bool)`

GetAgentTypeOk returns a tuple with the AgentType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentType

`func (o *OracleRequest) SetAgentType(v string)`

SetAgentType sets AgentType field to given value.

### HasAgentType

`func (o *OracleRequest) HasAgentType() bool`

HasAgentType returns a boolean if a field has been set.

### GetDepth

`func (o *OracleRequest) GetDepth() int32`

GetDepth returns the Depth field if non-nil, zero value otherwise.

### GetDepthOk

`func (o *OracleRequest) GetDepthOk() (*int32, bool)`

GetDepthOk returns a tuple with the Depth field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDepth

`func (o *OracleRequest) SetDepth(v int32)`

SetDepth sets Depth field to given value.

### HasDepth

`func (o *OracleRequest) HasDepth() bool`

HasDepth returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


