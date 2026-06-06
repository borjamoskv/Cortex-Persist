# AgentRegisterRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** |  | 
**AgentType** | Pointer to **string** | ai, human, oracle, system | [optional] [default to "ai"]
**PublicKey** | Pointer to **string** | Optional Ed25519 public key | [optional] [default to ""]

## Methods

### NewAgentRegisterRequest

`func NewAgentRegisterRequest(name string, ) *AgentRegisterRequest`

NewAgentRegisterRequest instantiates a new AgentRegisterRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAgentRegisterRequestWithDefaults

`func NewAgentRegisterRequestWithDefaults() *AgentRegisterRequest`

NewAgentRegisterRequestWithDefaults instantiates a new AgentRegisterRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *AgentRegisterRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *AgentRegisterRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *AgentRegisterRequest) SetName(v string)`

SetName sets Name field to given value.


### GetAgentType

`func (o *AgentRegisterRequest) GetAgentType() string`

GetAgentType returns the AgentType field if non-nil, zero value otherwise.

### GetAgentTypeOk

`func (o *AgentRegisterRequest) GetAgentTypeOk() (*string, bool)`

GetAgentTypeOk returns a tuple with the AgentType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentType

`func (o *AgentRegisterRequest) SetAgentType(v string)`

SetAgentType sets AgentType field to given value.

### HasAgentType

`func (o *AgentRegisterRequest) HasAgentType() bool`

HasAgentType returns a boolean if a field has been set.

### GetPublicKey

`func (o *AgentRegisterRequest) GetPublicKey() string`

GetPublicKey returns the PublicKey field if non-nil, zero value otherwise.

### GetPublicKeyOk

`func (o *AgentRegisterRequest) GetPublicKeyOk() (*string, bool)`

GetPublicKeyOk returns a tuple with the PublicKey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPublicKey

`func (o *AgentRegisterRequest) SetPublicKey(v string)`

SetPublicKey sets PublicKey field to given value.

### HasPublicKey

`func (o *AgentRegisterRequest) HasPublicKey() bool`

HasPublicKey returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


