<template>
  <div class="account-settings-info-view">
    <a-row :gutter="16" type="flex" justify="center">
      <a-col :order="isMobile ? 2 : 1" :md="24" :lg="16">
        <a-form layout="vertical">
          <a-form-item :label="$t('account.settings.basic.nickname')">
            <div class="editable-field" v-if="!editNicknameMode">
              <span class="field-value">{{ this.nickname }}</span>
              <a-icon type="edit" @click="editNickname" />
            </div>
            <a-form-item v-else>
              <a-input v-model="editedNickname" ref="nicknameInput" @keyup.enter="saveNickname" />
            </a-form-item>
          </a-form-item>

          <a-form-item :label="$t('account.settings.basic.profile')">
            <div class="editable-field" v-if="!editBioMode">
              <span class="field-value">{{ this.bio }}</span>
              <a-icon type="edit" @click="editBio" />
            </div>
            <a-form-item v-else>
              <a-textarea v-model="editedBio" rows="4" ref="bioInput" @keyup.enter="saveBio" />
            </a-form-item>
          </a-form-item>

          <a-form-item :label="$t('account.settings.basic.email')" :required="false">
            <div class="editable-field" v-if="!editEmailMode">
              <span class="field-value">{{ this.email }}</span>
              <a-icon type="edit" @click="editEmail" />
            </div>
            <a-form-item v-else>
              <a-input v-model="editedEmail" ref="emailInput" @keyup.enter="saveEmail" />
            </a-form-item>
          </a-form-item>

          <a-form-item>
            <a-button type="primary" @click="saveInfo()">{{ $t('account.settings.basic.update') }}</a-button>
          </a-form-item>
        </a-form>

      </a-col>
      <a-col :order="1" :md="24" :lg="8" :style="{ minHeight: '180px' }">
        <div class="ant-upload-preview avatar" @click="uploadAvatar()">
          <a-icon type="cloud-upload-o" class="upload-icon"/>
          <img :src="this.avatar">
          <input type="file" id="avatarInput" style="display: none" accept="image/*">
        </div>
      </a-col>

    </a-row>

    <avatar-modal ref="modal" @ok="setavatar"/>

  </div>
</template>

<script>
import AvatarModal from './AvatarModal'
import { baseMixin } from '@/store/app-mixin'
import axios from 'axios'

export default {
  mixins: [baseMixin],
  components: {
    AvatarModal
  },
  data () {
    return {
      nickname: localStorage.getItem('nickname'),
      bio: '',
      email: '',
      avatar: null,
      editNicknameMode: false,
      editBioMode: false,
      editEmailMode: false,
      editedNickname: '',
      editedBio: '',
      editedEmail: '',
      // cropper
      preview: {},
      option: {
        img: '/avatar2.jpg',
        info: true,
        size: 1,
        outputType: 'jpeg',
        canScale: false,
        autoCrop: true,
        // 只有自动截图开启 宽度高度才生效
        autoCropWidth: 180,
        autoCropHeight: 180,
        fixedBox: true,
        // 开启宽度和高度比例
        fixed: true,
        fixedNumber: [1, 1]
      }
    }
  },
  created () {
    this.fetchsettings(this.nickname)
  },
  methods: {
    setavatar (url) {
      this.option.img = url
    },
    fetchsettings (nickname) {
      axios.get('http://127.0.0.1:8000/api/users', { params: { nickname: nickname } })
        .then(res => {
          this.bio = res['data']['data']['bio']
          this.email = res['data']['email']
          this.avatar = res['data']['data']['avatar']
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    saveInfo () {
      axios.put('http://127.0.0.1:8000/api/users', { originalname: localStorage.getItem('nickname'), nickname: this.nickname, bio: this.bio, email: this.email })
        .then(res => {
          const currentname = res['data']['nickname']
          localStorage.setItem('nickname', currentname)
          alert('个人信息更新成功！')
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    editNickname () {
      this.editNicknameMode = true
      this.editedNickname = this.nickname
      this.$nextTick(() => {
        this.$refs.nicknameInput.focus()
      })
    },
    saveNickname () {
      this.nickname = this.editedNickname
      this.editNicknameMode = false
    },
    editBio () {
      this.editBioMode = true
      this.editedBio = this.bio
      this.$nextTick(() => {
        this.$refs.bioInput.focus()
      })
    },
    saveBio () {
      this.bio = this.editedBio
      this.editBioMode = false
    },
    editEmail () {
      this.editEmailMode = true
      this.editedEmail = this.email
      this.$nextTick(() => {
        this.$refs.emailInput.focus()
      })
    },
    saveEmail () {
      this.email = this.editedEmail
      this.editEmailMode = false
    },
    uploadAvatar () {
      // 找到文件上传的 input 元素
      var input = document.getElementById('avatarInput')

      // 设置 input 元素的 onchange 事件处理函数
      input.onchange = (e) => {
        var file = e.target.files[0] // 获取上传的文件
        var reader = new FileReader() // 创建一个文件读取器

        // 设置文件读取器的 onload 事件处理函数
        reader.onload = () => {
          var avatarImg = document.querySelector('.avatar img') // 找到 avatar 区域中的 img 元素
          avatarImg.src = reader.result // 设置 img 元素的 src 属性为读取的文件结果
          this.avatar = reader.result // 将读取的文件结果保存在名为 avatar 的变量中
          this.setAvatar(reader.result)
          localStorage.setItem('avatar', reader.result)
        }
        // 读取上传的文件
        reader.readAsDataURL(file)
      }

      // 触发点击文件上传的操作
      input.click()
    },
    setAvatar (avatar) {
      // console.log(avatar)
      axios.put('http://127.0.0.1:8000/api/users', { nickname: this.nickname, avatar: avatar })
      .then(res => {
        console.log('res')
      })
      .catch(err => {
        console.log(err)
      })
    }
  }
}
</script>

<style lang="less" scoped>

  .avatar-upload-wrapper {
    height: 200px;
    width: 100%;
  }

  .editable-field {
    display: flex;
    align-items: center;
  }

  .field-value {
    margin-right: 8px;
    font-size: 16px;
  }

  .ant-upload-preview {
    width: 180px;
    height: 180px;
    position: relative;
    margin: 0 auto;
    width: 100%;
    max-width: 180px;
    border-radius: 50%;
    box-shadow: 0 0 4px #ccc;

    .upload-icon {
      position: absolute;
      top: 0;
      right: 10px;
      font-size: 1.4rem;
      padding: 0.5rem;
      background: rgba(222, 221, 221, 0.7);
      border-radius: 50%;
      border: 1px solid rgba(0, 0, 0, 0.2);
    }
    & > .avatar {
      margin: 0 auto;
      width: 104px;
      height: 104px;
      margin-bottom: 20px;
      border-radius: 50%;
      overflow: hidden;
      img {
        height: 100%;
        width: 100%;
      }
      cursor: pointer;
    }
    .mask {
      opacity: 0;
      position: absolute;
      background: rgba(0,0,0,0.4);
      cursor: pointer;
      transition: opacity 0.4s;

      &:hover {
        opacity: 1;
      }

      i {
        font-size: 2rem;
        position: absolute;
        top: 50%;
        left: 50%;
        margin-left: -1rem;
        margin-top: -1rem;
        color: #d6d6d6;
      }
    }

    img, .mask {
      width: 100%;
      max-width: 180px;
      height: 100%;
      border-radius: 50%;
      overflow: hidden;
    }
  }
</style>
