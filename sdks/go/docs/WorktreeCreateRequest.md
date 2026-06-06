# WorktreeCreateRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**BranchName** | **string** | Branch to isolate | 
**BasePath** | Pointer to **NullableString** | Optional root for worktrees | [optional] 

## Methods

### NewWorktreeCreateRequest

`func NewWorktreeCreateRequest(branchName string, ) *WorktreeCreateRequest`

NewWorktreeCreateRequest instantiates a new WorktreeCreateRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWorktreeCreateRequestWithDefaults

`func NewWorktreeCreateRequestWithDefaults() *WorktreeCreateRequest`

NewWorktreeCreateRequestWithDefaults instantiates a new WorktreeCreateRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetBranchName

`func (o *WorktreeCreateRequest) GetBranchName() string`

GetBranchName returns the BranchName field if non-nil, zero value otherwise.

### GetBranchNameOk

`func (o *WorktreeCreateRequest) GetBranchNameOk() (*string, bool)`

GetBranchNameOk returns a tuple with the BranchName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBranchName

`func (o *WorktreeCreateRequest) SetBranchName(v string)`

SetBranchName sets BranchName field to given value.


### GetBasePath

`func (o *WorktreeCreateRequest) GetBasePath() string`

GetBasePath returns the BasePath field if non-nil, zero value otherwise.

### GetBasePathOk

`func (o *WorktreeCreateRequest) GetBasePathOk() (*string, bool)`

GetBasePathOk returns a tuple with the BasePath field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBasePath

`func (o *WorktreeCreateRequest) SetBasePath(v string)`

SetBasePath sets BasePath field to given value.

### HasBasePath

`func (o *WorktreeCreateRequest) HasBasePath() bool`

HasBasePath returns a boolean if a field has been set.

### SetBasePathNil

`func (o *WorktreeCreateRequest) SetBasePathNil(b bool)`

 SetBasePathNil sets the value for BasePath to be an explicit nil

### UnsetBasePath
`func (o *WorktreeCreateRequest) UnsetBasePath()`

UnsetBasePath ensures that no value is present for BasePath, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


