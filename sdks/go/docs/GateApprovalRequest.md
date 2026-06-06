# GateApprovalRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Signature** | **string** | HMAC-SHA256 signature of the challenge | 
**OperatorId** | Pointer to **NullableString** | Operator identifier | [optional] 

## Methods

### NewGateApprovalRequest

`func NewGateApprovalRequest(signature string, ) *GateApprovalRequest`

NewGateApprovalRequest instantiates a new GateApprovalRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewGateApprovalRequestWithDefaults

`func NewGateApprovalRequestWithDefaults() *GateApprovalRequest`

NewGateApprovalRequestWithDefaults instantiates a new GateApprovalRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSignature

`func (o *GateApprovalRequest) GetSignature() string`

GetSignature returns the Signature field if non-nil, zero value otherwise.

### GetSignatureOk

`func (o *GateApprovalRequest) GetSignatureOk() (*string, bool)`

GetSignatureOk returns a tuple with the Signature field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSignature

`func (o *GateApprovalRequest) SetSignature(v string)`

SetSignature sets Signature field to given value.


### GetOperatorId

`func (o *GateApprovalRequest) GetOperatorId() string`

GetOperatorId returns the OperatorId field if non-nil, zero value otherwise.

### GetOperatorIdOk

`func (o *GateApprovalRequest) GetOperatorIdOk() (*string, bool)`

GetOperatorIdOk returns a tuple with the OperatorId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOperatorId

`func (o *GateApprovalRequest) SetOperatorId(v string)`

SetOperatorId sets OperatorId field to given value.

### HasOperatorId

`func (o *GateApprovalRequest) HasOperatorId() bool`

HasOperatorId returns a boolean if a field has been set.

### SetOperatorIdNil

`func (o *GateApprovalRequest) SetOperatorIdNil(b bool)`

 SetOperatorIdNil sets the value for OperatorId to be an explicit nil

### UnsetOperatorId
`func (o *GateApprovalRequest) UnsetOperatorId()`

UnsetOperatorId ensures that no value is present for OperatorId, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


