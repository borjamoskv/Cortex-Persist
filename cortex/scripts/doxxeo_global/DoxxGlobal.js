/**
 * ============================================================================
 * PROTOCOLO NÉMESIS: TIERRA QUEMADA (GLOBAL DOXXER)
 * ============================================================================
 * Objetivo: Escalar la denuncia de las Wallets de Foizur a las bases de datos
 * globales de inteligencia de amenazas web3.
 * 
 * Target 1: Chainabuse (La API más usada por wallets para etiquetar scams)
 * Target 2: ScamSniffer (El plugin anti-phishing número 1 en Chrome)
 * Target 3: CryptoScamDB
 * ============================================================================
 */

const fs = require('node:fs');

console.log("🌍 INICIANDO PROTOCOLO: TIERRA QUEMADA (GLOBAL DOXXER) 🌍\n");

const COMPROMISED_WALLETS = [
    // Tier 1 - Nodos Centrales
    "0x701e13e8da8ef04cd40e92f21869932fe5e35555", // Master Deployer
    "0x0083022683e56a51ef1199573411ba6c2ab60000", // Consolidador Maestro
    "0x54ba52cbd043b0b2e11a6823a910360e31bb2544", // Sweeper/Deployer
    // Tier 2 - Contratos Maliciosos & EIP-7702
    "0xEeCAc0ac4143bbfb60a497e43646c0002285902c", // EIP-7702 delegation target
    "0xf428114411E883F62b9a4007723648a88e7679eE", // Fake_Phishing1685665
    "0x7cd3717264da69a9472d8cd2580e124a57982754", // Drainer contract code
    // Tier 3 - Operativas & Funders
    "0x79940B12230B7534d934D18DbC7DD84512FC98dE", // Fake_Phishing1616687
    "0x87fce75dcc4cb8e3e4b80dc33b60af97cf53ed5b", // Fake_Phishing1616684
    "0x0000ee5760d1f3556f9c2052f77326e402d10000", // Fake_Phishing1509275 (funder)
    "0x2CfF890f0378a11913B6129b2e97417A2C302680", // Funder del Sweeper
    // Tier 4 - Recolección Base & Polygon L2s
    "0x86a4C6aD2726ac5aef59b35700620aae7d80f982", // Base Collection
    "0x8a7D09167de635332d22b0843bece515da38Dec8", // Base Collection
    "0xac831A730e34f71f40a8672cf5e5cba29892a07f", // Base Collection
    "0x9e72b4a743f29dbb6a40f00b175525ea3249e4d4", // yakaligaskuy.base.eth
    "0xf9F4538CA88c9a4C7b715bbADa68404AfC33d0ed", // Base Collection 2
    "0x2538587c5cEaAE6FFA1E9FCe93BDAdD3227c42A1", // Base Collection 3
    "0x0200d4D4cbE9Ba4ed322E9e5b8229fbEdead0000", // Polygon Collection 1
    "0x8D0B66c1d1800a1d0F7483795d586F9C81610653", // Polygon Collection 2
    "0xbFE129315f75dD7BA60Ec85B4024E0FE1264FB13", // Unknown Collection
    "0x1D0f3F1599A710486818F1D1002aDF5E9c0f49A8", // Arkham Late Injection Node
    // Extraidas en Fase 1 y Nodo Hidra L1
    "0x7df263b72c722f46ba54589d9e4672642", // Nodo Central (arbithumarb.eth)
    "0x7bdc9ce05dc366f07e0cce077f5203ce834cc04c",
    "0xb7c8ad2b6fc2ad542fbadde7a9c8491bb7b4cdd5",
    "0xD0De574C37b6de2AE1A614fFEBb939768670CD7F",
    // --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---
    "0x7df263b72c722f46ba54589d9e4672642", // Swarm L4-L5 Mule
    "0x06060c5e3a090a1aff282bbec1eb7db7bdab7a60", // Swarm L4-L5 Mule
    "0x304cee3c3905af315519a2b94b8992967c6cb566", // Swarm L4-L5 Mule
    "0x5102bb07597ebe24db4a42757286437fa881987e", // Swarm L4-L5 Mule
    "0xffc7fc93190a5e967d282d7b04813badb543fabd", // Swarm L4-L5 Mule
    "0xeef044e2932043e722ea4de4896364d7193bad8c", // Swarm L4-L5 Mule
    "0x05a3324969ad8a10c013009601a3cba905d124f6", // Swarm L4-L5 Mule
    "0x360c801545527c2bd707fac247bb2bcb20cefbce", // Swarm L4-L5 Mule
    "0x7727e58e58a2a1321df80d5911fbb7b00e83040e", // Swarm L4-L5 Mule
    "0x8c1609fdc3967050ecb67564fc3fa010a80f439b", // Swarm L4-L5 Mule
    "0xaf9e5109b575c7c7dd84db8432400fd3809211d2", // Swarm L4-L5 Mule
    "0xbb1c92fa8417c77074b8d379b03454992c0a55ab", // Swarm L4-L5 Mule
    "0xb795a847dcec8c8c68c71df1e8111864f9998883", // Swarm L4-L5 Mule
    "0xd9f5e44bb696e26421bf7f6a796d90251932df96", // Swarm L4-L5 Mule
    "0xfe7f7d1e7628e37fef9b5fc911f24f10be12f052", // Swarm L4-L5 Mule
    "0xe08e6650484834f94e387558ed700021a0294aea", // Swarm L4-L5 Mule
    "0xae8d70a4a30dfa66b25a0eddf7201a44a6291b83", // Swarm L4-L5 Mule
    "0x1358c9394441c303a7079b643f91f46dbb1155c3", // Swarm L4-L5 Mule
    "0x46a54aac5eb34e99785ea94c52ddf8e76599a8ff", // Swarm L4-L5 Mule
    "0x61090efc55fd5d258651910b8a125f387d33a2db", // Swarm L4-L5 Mule
    "0x43ec3d4807f0da8d06e71bf1355a21fa4fa29b83", // Swarm L4-L5 Mule
    "0x51ceb56fadbb15811ff6f1d1614c20284e6a3f4d", // Swarm L4-L5 Mule
    "0x569853ca773229433d4d2fba92d01c0bc86fe39a", // Swarm L4-L5 Mule
    "0x91b93139e4849ed73d6a620f4e6bef36b95873f8", // Swarm L4-L5 Mule
    "0x91a93133afeabe513c2b0b768889ab77c89059f7", // Swarm L4-L5 Mule
    "0xe60662a2578afdf2e654171336df551860ecea4d", // Swarm L4-L5 Mule
    "0x7f662348efbed37d84aa3adbe193c9723a9e864a", // Swarm L4-L5 Mule
    "0x3ac561e7867b8f1b86200b1a6a1ee66b2bfcf4fc", // Swarm L4-L5 Mule
    "0x54b62f283d91d70ba89da37244782d0a485f242e", // Swarm L4-L5 Mule
    "0x54ba5ed336977c25c8e2ea7422eb7e8527ba420e", // Swarm L4-L5 Mule
    "0x44046fa09530ff629bf417b5239bc7655c86d2b3", // Swarm L4-L5 Mule
    "0x7a3cbb058bb85d70f53bcb67f4d9d94a985160d3", // Swarm L4-L5 Mule
    "0x6107c76c46a866730adf2bd6bde101efca024b63", // Swarm L4-L5 Mule
    "0x7cf91cbbcd825fe852b923985cd49fa5d30a636e", // Swarm L4-L5 Mule
    "0x15be04d6dbd93c173f258ce9ba196586dfb51e89", // Swarm L4-L5 Mule
    "0x24275aa8b94c90845a6c6c58b63710e039c8b990", // Swarm L4-L5 Mule
    "0x41ac2118ef6746ddaa0a3c8b1ef3edeb755a9940", // Swarm L4-L5 Mule
    "0x5bc5fb22243ef08ee001ecd054e4f8d70785bd12", // Swarm L4-L5 Mule
    "0xa4478388ff17e24c5449357d51d9d00f8d42d2b2", // Swarm L4-L5 Mule
    "0xed91c3583124bcfccd349db6adfc23c68629f71f", // Swarm L4-L5 Mule
    "0x651f2bde1610092ace7c4f2f1c5cc8c3137d4b7d", // Swarm L4-L5 Mule
    "0x5e891205de76b5b5c02444d4777840fd28970a85", // Swarm L4-L5 Mule
    "0x225cd05b6e4cddc094576232d04929804bef6af2", // Swarm L4-L5 Mule
    "0x52a70b518db85fe032d04127ec56f5a890bb77f7", // Swarm L4-L5 Mule
    // --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---
    "0x7df263b72c722f46ba54589d9e4672642", // Swarm L4-L5 Mule
    "0x382bb0d7cb4137a464949223b19e0a0ebd8c14c1", // Swarm L4-L5 Mule
    "0x6cf94a19cf74ca99edfdfa2323ec13f74feddd3b", // Swarm L4-L5 Mule
    "0x3fcb37954e11bbcefdf222d5e4e25e8646348ab1", // Swarm L4-L5 Mule
    "0x17d076d4e333e0721e72cae18353809af10c2963", // Swarm L4-L5 Mule
    "0x2d989a48270c95f72bfbd4971ac88cceb2f16f00", // Swarm L4-L5 Mule
    "0xd95727578e8d0673c26a241210afc4188c5e6c0b", // Swarm L4-L5 Mule
    "0xd08c2b4a343f9f15c94ce4a9c92c83a07474de81", // Swarm L4-L5 Mule
    "0x1890ead22859b3385edb759960e51d318e4f8029", // Swarm L4-L5 Mule
    "0xa179dcb88adc0ce0df6806b53c16d762cdf9d2eb", // Swarm L4-L5 Mule
    "0xa344e49c93fa45676d58e67b0c3ff189a0a0ba66", // Swarm L4-L5 Mule
    "0xf2bb57e3e6276c3ff5a24608c036c349fb1d7c41", // Swarm L4-L5 Mule
    "0x66847466db2d1c6aec461bcb9c792be9d7335fcc", // Swarm L4-L5 Mule
    "0x4bbafbed84584d4dcf35284f843860efa1622542", // Swarm L4-L5 Mule
    "0x3ce99a444e827e93317a81e9cb774249bf68b57d", // Swarm L4-L5 Mule
    "0xa9d8f6762cea2261f11486fbbae0788c02bab017", // Swarm L4-L5 Mule
    "0x9c6b7015501c0c68f2f3fa7a074cf1e33427d1cf", // Swarm L4-L5 Mule
    "0x9f5e5aa29919c515520e15aee6f115ceae7661dd", // Swarm L4-L5 Mule
    "0x316f1fda4338cf587cb54feff0e6d94f57cb63d6", // Swarm L4-L5 Mule
    "0xe74cf639b7f6c272c3b2a11155638999a186b606", // Swarm L4-L5 Mule
    "0x68ad63e2ca64364147b55ff4595efcc1581a2e09", // Swarm L4-L5 Mule
    "0xdeb40586ec87230392d1bbda825b6d57b2140898", // Swarm L4-L5 Mule
    "0x55a62b779ba05acc4ca78475442361ecd3e52603", // Swarm L4-L5 Mule
    "0x4dd377a4d6951a5832443c4743e867d59d8476a1", // Swarm L4-L5 Mule
    "0xf52edfca32ab155116bee64bd3e93ee681575f11", // Swarm L4-L5 Mule
    "0x1f4abb70c4195542df59c1f023747dd7e3f2baa8", // Swarm L4-L5 Mule
    "0xb3f3a28778a78a1e0d7684060ee57cdf39bcc187", // Swarm L4-L5 Mule
    "0x8dbc033487f26996754fb3d7e673ef28f9629dde", // Swarm L4-L5 Mule
    "0x60704a78dbae1eff60261d0a42c16c0478549fcf", // Swarm L4-L5 Mule
    "0x77d92fbc16161a67f5d760016fcbdc20eb492ac1", // Swarm L4-L5 Mule
    "0x8fbb908a193afd9d13fd8241aedb4ac47b9877aa", // Swarm L4-L5 Mule
    "0x08b342b8e664a468595bd4bd5c796b9e9212b42b", // Swarm L4-L5 Mule
    "0x02bad3416cfe17183b855105b874bb2e0a0638fd", // Swarm L4-L5 Mule
    "0x71a2ce726943c022d369ca23783dacc773438d0d", // Swarm L4-L5 Mule
    "0xb1799b08528d57c66792a00ee359e3c49464feda", // Swarm L4-L5 Mule
    "0x85bece11f644eef0e53cdad4a1487d580e6714cd", // Swarm L4-L5 Mule
    "0xca259f82fd6276d3cc6ee399e85aa2b93ee2d4ee", // Swarm L4-L5 Mule
    "0x591114c2efaea017c905f3ecd3d1b47b6bf40d88", // Swarm L4-L5 Mule
    "0x917df0269096751dbe8b1daea6077c08f0b73e49", // Swarm L4-L5 Mule
    "0xc8ad5cf2d308e90db2ef3efc5b860c9cdf8c70a2", // Swarm L4-L5 Mule
    "0x6dbcb27816de651c4df23976a9fdc4b4edefad99", // Swarm L4-L5 Mule
    "0xfde92c8fbe81a63193e7eed05cf1d5b0e7f3db64", // Swarm L4-L5 Mule
    "0x52efa080222415b80760cf031aa9c0c8088da432", // Swarm L4-L5 Mule
    "0x7ad42c515976049ef9d15e4ea34b31f3d231cf2e", // Swarm L4-L5 Mule
    "0xf59b9709eec141889eac79b2533f018154a66d5d", // Swarm L4-L5 Mule
    "0xff2101f31beb9483821d918a48d3162811c841c2", // Swarm L4-L5 Mule
    "0x561bb777dde4fa642ea0447f2e367b7119d824bb", // Swarm L4-L5 Mule
    "0x9b9a392e2a4057097aad81f6a44936da8a9d6d0f", // Swarm L4-L5 Mule
    "0xa8948b0b1d503ca9b1e7dc495d331488a2b5b416", // Swarm L4-L5 Mule
    "0x9018b6b6cea81ef5c58091a2b4bc0a48ef45f8f6", // Swarm L4-L5 Mule
    "0x59598f1e88b965d54fe842e5245bb6d4578c7ecd", // Swarm L4-L5 Mule
    "0x2b70bb9b85179eba2153b1c33b9028d009a6474a", // Swarm L4-L5 Mule
    "0x551840f1e7aaa9bbd66847d1f0d21555b2e498d5", // Swarm L4-L5 Mule
    "0xd02dac21497039c0a68f4326e4b0db8f4ef785a5", // Swarm L4-L5 Mule
    "0xf0ae6324737583939f67aef14f66ac00aec99dfe", // Swarm L4-L5 Mule
    "0xa6f8889a6df122cbfe0b75aa54d0a715987bf427", // Swarm L4-L5 Mule
    "0x3cb8090dd6d07ff1d36c3fd203dbabed880aaf89", // Swarm L4-L5 Mule
    "0x0bd6262b7addc8cb973e77c1d21873521aa94219", // Swarm L4-L5 Mule
    // --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---
    "0x7df263b72c722f46ba54589d9e4672642", // Swarm L4-L5 Mule
    "0xeffa8221f0832de9299afb8dbd705ec07165fbf4", // Swarm L4-L5 Mule
    "0x475e84b1139a8ed2b2e30e2c54474d8c3cb85f1c", // Swarm L4-L5 Mule
    "0xcaad5705219b2696ea68860a89209876cc6cd17d", // Swarm L4-L5 Mule
    "0xaccc5c09a18bb5e794b2417af6c247f6b2544410", // Swarm L4-L5 Mule
    "0x74be7efbf339e08b331e13f255109e2a17f02b90", // Swarm L4-L5 Mule
    "0x2eba78c47ca0df513ba22f49db0b6ddec35ba644", // Swarm L4-L5 Mule
    "0x33199773faea4f196ab6868d640de33a0460b799", // Swarm L4-L5 Mule
    "0xc5309eb33f70b840095b15c6f985684357971543", // Swarm L4-L5 Mule
    "0x100dc39e9e02fa575553ecf74d900917886dff1a", // Swarm L4-L5 Mule
    "0x1eb5279c69e7efe7527219edfcb81ef657cd219a", // Swarm L4-L5 Mule
    "0xc6372becf9ccd565aed7d49eb80cd74998476247", // Swarm L4-L5 Mule
    "0x6f00e135bb2fc2437b3bc03eec6546c6964696a0", // Swarm L4-L5 Mule
    "0xf6123ef4e7254511ad01721dfc1992a2b34b918c", // Swarm L4-L5 Mule
    "0x2dcb2c4ad51706ca69f7fcfd1ac950f79b0ef32c", // Swarm L4-L5 Mule
    "0xfa0ae52d56981bbd9fd3f8b727b5efb5ee09e603", // Swarm L4-L5 Mule
    "0xfa774005598a6d7bb8ad5ed6230da869d205e134", // Swarm L4-L5 Mule
    "0x7dfbd092781f8b963dbadac1759b7223a69b7d37", // Swarm L4-L5 Mule
    "0xb56487dbf72611b6f1a4277de7ae2e739682be6e", // Swarm L4-L5 Mule
    "0x8584e9941bf57c07162bb46600565c63f76719c3", // Swarm L4-L5 Mule
    "0x9f6783b86c068c9d9b7d423dcfd8135514e605ef", // Swarm L4-L5 Mule
    "0x1b404d9a081dc15ca2a0e01037de8e001fca0537", // Swarm L4-L5 Mule
    "0x9300978cd47c6cfe032928fb0d4a29db7417f0ee", // Swarm L4-L5 Mule
    "0x569fd83162d15b73591a1d859181d28c4d9c8f75", // Swarm L4-L5 Mule
    "0x0237bdb6e713f234f62cf6d03b47f253f67f641e", // Swarm L4-L5 Mule
    "0xfa3bf614cc3acb47dc57b34dd7cfa247005771d1", // Swarm L4-L5 Mule
    "0x9490856c94c674d589da41fa9c3ab70a51bb1216", // Swarm L4-L5 Mule
    "0x09d26df4913e2d3e13a2a096b28524721bb5f90f", // Swarm L4-L5 Mule
    "0xe65122355f2643e4c04345aab1049299826de907", // Swarm L4-L5 Mule
    "0xf54efcd2d1ece6987ea5e939fb73811d0d1f80e0", // Swarm L4-L5 Mule
    "0x248f8b92aed105c8c2e1e5b983b740da25888177", // Swarm L4-L5 Mule
    "0x0e2f4be7da80bf1c26099b2ca4af13551911b56f", // Swarm L4-L5 Mule
    "0x9a11bc6e501d43d37fb53c4bfa26872c36f2d1f2", // Swarm L4-L5 Mule
    "0xf968a2da3652207bfba3d87a01563dfd017543fc", // Swarm L4-L5 Mule
    "0xdfc2c7fd7de1f122028588d33477b0f37cd8188f", // Swarm L4-L5 Mule
    "0xa4aec6926f29dee5de97ed0eafb342768409c68e", // Swarm L4-L5 Mule
    "0x0840a7c2e40b1985975a1d2b4d134a2eb49c2820", // Swarm L4-L5 Mule
    "0xcfaf294521f5db1134596abddc3b4aa4ebfa18ff", // Swarm L4-L5 Mule
    "0x293c46cf012705a458754a90b4108c6c57329ac6", // Swarm L4-L5 Mule
    "0x3934df775d9ae81ae605b985f76c79cdadb4de67", // Swarm L4-L5 Mule
    "0x47e0c19d246fc2fd2bec6278cea66495e2557014", // Swarm L4-L5 Mule
    "0x0239ce9b8446a135bd25f33e8f124938ccea2240", // Swarm L4-L5 Mule
    "0x1e703da74a914f45b7d0d70399c67f525e25ebf8", // Swarm L4-L5 Mule
    "0x9683e31acc2f2648e8304c1987cdb597c6487f7e", // Swarm L4-L5 Mule
    "0x05e88e92184e0c7a1f1e23c15e8a3c367f24b228", // Swarm L4-L5 Mule
    "0x2bb0bf789c7d3b007dbf109ed87627eaedf9a07e", // Swarm L4-L5 Mule
    "0x0579564ca7a7d8ef2b50a69339ed53e2639350cd", // Swarm L4-L5 Mule
    "0x21a8c227bcd91424c4531548c2a9e4f7b7fe82cc", // Swarm L4-L5 Mule
    "0xc77567a536144d6c34db32edde17c36df9679dce", // Swarm L4-L5 Mule
    "0x7b9144006d8fa2d452058cd107bbce4c30416f4c", // Swarm L4-L5 Mule
    "0x26c37224cd9593e4103514ffcb2602e401349002", // Swarm L4-L5 Mule
    "0xce5998a7137aa3269c8d6d85a8a492c7e2370200", // Swarm L4-L5 Mule
    "0x6be1de28b4312e9e862bb61cad819a2ebb53f80b", // Swarm L4-L5 Mule
    "0x4170bf1590c9daab069f99003730ee8081f1a50c", // Swarm L4-L5 Mule
    "0xb2dd6cde03988a4d78a3c66fd29fe5ef2a6c80f9", // Swarm L4-L5 Mule
    "0xffbdb95e358b3e0a5fd504ac1442ff20380ec0f5", // Swarm L4-L5 Mule
    "0xb1f4640beb1551801b7ca96d534885a81a80f8c8", // Swarm L4-L5 Mule
    "0x504e6e08383a05234d23e8aad9a2e05105c78bfb", // Swarm L4-L5 Mule
    "0x3d0672b4d6b3209014351e8f122fa1ba9fc2b39c", // Swarm L4-L5 Mule
    "0x0c614bc3ae5cd27af743a6a88b83548f6a32fa84", // Swarm L4-L5 Mule
    "0xaaccfd47a2816e1c073bca6438c082d8278c9536", // Swarm L4-L5 Mule
    "0x1697d216b611f8144329035bbacc8354b20df5a2", // Swarm L4-L5 Mule
    "0xa93a83ba9ecc5df1f67d0933305b7b7c980b823b", // Swarm L4-L5 Mule
    "0x7169e2f18ff586e60c611b36ed6fb3167900c1cc", // Swarm L4-L5 Mule
    "0x686651cde47ad0b8c62a46080e8de86c3ea60412", // Swarm L4-L5 Mule
    "0xcb881e1aacd8c9d8c216ebfbb2ff838922c23b57", // Swarm L4-L5 Mule
    "0x524300cf555f60cba09a08fc77605f6cb3bf3a6f", // Swarm L4-L5 Mule
    "0xc85899ede20ab6b9bb9ffc8142c3a72925542ddb", // Swarm L4-L5 Mule
    "0xc21067155560c99db5a3b3098e5c602321d4e560", // Swarm L4-L5 Mule
    "0x25bb6f80821e8f07faf1935b7d1c554bc0a70ad5", // Swarm L4-L5 Mule
    // --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---
    "0x7df263b72c722f46ba54589d9e4672642", // Swarm L4-L5 Mule
    "0x698b84ddf8677a732d91d10447339db227a42a68", // Swarm L4-L5 Mule
    "0x8b4a939a19788066c5aeb5524a60504c52c72019", // Swarm L4-L5 Mule
    "0xe08e05e21c59f38cfb3e445d62afd5eaf1d84de4", // Swarm L4-L5 Mule
    "0x0573e5e310a13029d2ce6512115619c0908e463d", // Swarm L4-L5 Mule
    "0xac99bf9b725334f82feee18866fd89816bf57039", // Swarm L4-L5 Mule
    "0x12cf80a98d27a7e54963b0c3eba91f330b6a2fe7", // Swarm L4-L5 Mule
    "0xef062a1c5db00d1008890b5d3d67ad8d19d90060", // Swarm L4-L5 Mule
    "0x57064689cb2c9107642070f3fd439fdb921ec7e1", // Swarm L4-L5 Mule
    "0x50e46c70a6887adff904a8ab1c13ed2760ca883f", // Swarm L4-L5 Mule
    "0x7311711c61ef1a60db52025a3be6afb52c389883", // Swarm L4-L5 Mule
    "0xcce4c76d152a13359eee225b53f48f3aa5a82cab", // Swarm L4-L5 Mule
    "0x1543518e5ff0d287c67850c2bad34f9f9a47b7f8", // Swarm L4-L5 Mule
    "0x56fe8264388fa0f6235baf94ea1d31695420c1d1", // Swarm L4-L5 Mule
    "0x9fb10c4943803f991ae6117367008a37059042b7", // Swarm L4-L5 Mule
    "0x193d6a778db11737b48059e0e92b55b88f5a16bf", // Swarm L4-L5 Mule
    "0x20192169b7cc25a2c5ed538deaeaeb72121fa42c", // Swarm L4-L5 Mule
    "0x14e236b42c498c2bf14751d694c984e9a23a7c77", // Swarm L4-L5 Mule
    "0xff01235c0f1203fff64eb9ce263831b2aeb947a8", // Swarm L4-L5 Mule
    "0x95c337cbda6c15f11d45b39ce0ee37240c583063", // Swarm L4-L5 Mule
    "0xc2ca32d7ce8f94af0f69aeb424bf47f33c9187c9", // Swarm L4-L5 Mule
    "0xf81ed2517a59531544ea8423c0d9b8a12887ed8c", // Swarm L4-L5 Mule
    "0x04a288c6c9efe8e2b6ceef01a2763c2e4ca7bcd3", // Swarm L4-L5 Mule
    "0xf1f852c5ed3fd666059bd1295772791667c151e5", // Swarm L4-L5 Mule
    "0xa6d33fe7a178aaac75ff522760f9843225ec6e3d", // Swarm L4-L5 Mule
    "0x6961c7d0f3783deebf11e9bc228a370e163850e7", // Swarm L4-L5 Mule
    "0x81d5f816eb05094679f7871058c8bf94db936085", // Swarm L4-L5 Mule
    "0xa8f5b396b1f2470ec575bba0be9bc4d4828a0c23", // Swarm L4-L5 Mule
    "0xc115402b002a670ead82908b87f2d42fb91fae40", // Swarm L4-L5 Mule
    "0x90aa40b21041006e2e992db4f3c72a669d3c19b0", // Swarm L4-L5 Mule
    "0x1a09e59f031777f0ea90999653c50299940192ef", // Swarm L4-L5 Mule
    "0x6dd678f8ccb4e3e35621608711e9ea2b790ae823", // Swarm L4-L5 Mule
    "0xb5ab3382907a3716f9a1828bb25b9a7cb950ea56", // Swarm L4-L5 Mule
    "0xf463d140142f27cbed15af856f14556b477e1fc1", // Swarm L4-L5 Mule
    "0xb2806c4419f82ad973fda1348dd7764cf940737e", // Swarm L4-L5 Mule
    "0xfba4e8a1cf911b5085e16f6f50572c206ed57d4c", // Swarm L4-L5 Mule
    "0xa02e65937d1194d5f17104dfcc77c8231ee9c807", // Swarm L4-L5 Mule
    "0x3ee4f80bf10bf9c447888d033b353cfde79b644a", // Swarm L4-L5 Mule
    "0x0f1ffed2d2446727ea7485234a4871bb2b0dbf72", // Swarm L4-L5 Mule
    "0xaac19ab961389ed6d5823f306e0b29973ab2d6e4", // Swarm L4-L5 Mule
    "0x0078ba245f5ca96e174e43dc50b94a56410cbd24", // Swarm L4-L5 Mule
    "0xa3f21a9bfa393b938c347eded352f8f3c33c9a17", // Swarm L4-L5 Mule
    "0x610339eabc90c72e577798108d7ba23cc61a4eaa", // Swarm L4-L5 Mule
    "0xa97785866dd74dd56d62bac6ab2ad715f95e7f3b", // Swarm L4-L5 Mule
    "0xf300f616be6e4db2d341ad7e1c0e1f266e8a3d60", // Swarm L4-L5 Mule
    "0x40adb1d3ab138abcebc956392578cef718bf6e4d", // Swarm L4-L5 Mule
    "0xd9d49d1d962bf03967b94c1f672b93032e970326", // Swarm L4-L5 Mule
    "0x6120e979d35f38392741f1adaf432cdc761eb35b", // Swarm L4-L5 Mule
    "0x4ae9b8ab05a044c555bb95da0f5d915df3d52351", // Swarm L4-L5 Mule
    "0x6780a6d3b085222f87dcd20c8f342eea9424ba0c", // Swarm L4-L5 Mule
    "0x5896bee084ffac96ef03988568974e50ff0addd7", // Swarm L4-L5 Mule
];

const EVIDENCE = "https://borjamoskv.substack.com/p/take-the-eth-and-run";
const MALWARE_FAMILY = "EIP-7702 Phishing / ChainId 0 Exploit";
const ATTACKER_ALIAS = "Foizur (@arbithumarb)";

// --- GENERADOR DE PAYLOADS PARA APIs DE SEGURIDAD ---

console.log("🧨 Construyendo Payloads de Denuncia para Bases de Datos Globales...\n");

// Clean wallets (Deduplicate, validate length to 42 chars)
const cleanedWallets = Array.from(
    new Set(COMPROMISED_WALLETS.map(w => w.toLowerCase()))
).filter(w => /^0x[a-f0-9]{40}$/i.test(w));

const chainAbusePayload = {
    "scammer": ATTACKER_ALIAS,
    "addresses": cleanedWallets.map(w => ({ address: w, chain: "ETH/BASE/ARB" })),
    "category": "PHISHING",
    "description": `Attacker orchestrating EIP-7702 (chainId 0) delegations to drain wallets. Using phishing sites (.vercel.app) to spoof Safe/OpenSea. Full autopsy: ${EVIDENCE}`,
    "evidence_url": EVIDENCE
};

const scamSnifferPayload = {
    "malicious_contracts": Array.from(new Set(["0x7bdc9ce05dc366f07e0cce077f5203ce834cc04c"].map(w => w.toLowerCase()))),
    "malicious_eoa": Array.from(new Set(["0xb7c8ad2b6fc2ad542fbadde7a9c8491bb7b4cdd5", "0xD0De574C37b6de2AE1A614fFEBb939768670CD7F"].map(w => w.toLowerCase()))),
    "type": "Wallet Drainer",
    "notes": `EIP-7702 exploit. See: ${EVIDENCE}`
};

// Escribimos los payloads para ejecución manual rápida.
fs.writeFileSync('chainabuse_report.json', JSON.stringify(chainAbusePayload, null, 2));
fs.writeFileSync('scamsniffer_report.json', JSON.stringify(scamSnifferPayload, null, 2));

console.log("✅ Payloads generados.");

console.log("\n=======================================================");
console.log("🔥 RUTA DE EJECUCIÓN SOBERANA (DOXXEO MAXIMUM) 🔥");
console.log("=======================================================");
console.log("Las APIs de inteligencias de amenazas requieren validación Humana/Web3");
console.log("para evitar bombardeos de spam (bots reportando inocentes).");
console.log("\nEjecuta el protocolo visitando estos 2 nodos centrales:");
console.log("1. CHAINABUSE (La base de TRM Labs que usan todos los exchanges):");
console.log("   -> https://www.chainabuse.com/report");
console.log(`   (Copia los datos de 'chainabuse_report.json' aquí)`);
console.log("\n2. SCAMSNIFFER (Para bloquear sus wallets en MetaMask/Rabby):");
console.log("   -> Entra en su Discord: https://discord.gg/scamsniffer");
console.log(`   -> Ve al canal #report-scam y pega el contenido de 'scamsniffer_report.json'`);
console.log("\nAl hacer esto, cualquier usuario con una wallet moderna o extensión de seguridad");
console.log("recibirá un aviso de 'MALICIOUS ADDRESS' en pantalla roja si Foizur intenta");
console.log("interactuar con ellos. Su liquidez y operativa quedarán neutralizadas.");
console.log("=======================================================\n");
