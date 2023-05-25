<template>
  <div>
    <a-form @submit="handleSubmit">
      <a-form-item label="新密码">
        <a-input v-model="newPassword" :type="showPassword ? 'text' : 'password'" :class="inputClass">
          <template #suffix>
            <a v-show="!showPassword" @click="showPassword = true">显示</a>
            <a v-show="showPassword" @click="showPassword = false">隐藏</a>
          </template>
        </a-input>
      </a-form-item>
      <a-form-item label="确认密码">
        <a-input v-model="confirmPassword" :type="showPassword ? 'text' : 'password'" :class="inputClass"></a-input>
      </a-form-item>
      <a-form-item>
        <a-button type="primary" html-type="submit">确认修改</a-button>
      </a-form-item>
      <div class="delete-account-section">
        <h2>注销账号</h2>
        <a-button type="danger" @click="confirmDelete">注销账号</a-button>
      </div>
    </a-form>
  </div>
</template>

<script>
import { axios } from '@/utils/request'

export default {
  data () {
    return {
      newPassword: '',
      confirmPassword: '',
      showPassword: false,
      inputClass: 'small-input' // 添加自定义的class
    }
  },
  methods: {
    handleSubmit () {
      if (this.newPassword === this.confirmPassword) {
        // 执行密码修改逻辑
        console.log(this.newPassword)
        axios
          .put('http://127.0.0.1:8000/api/users', {
            nickname: localStorage.getItem('nickname'),
            password: this.newPassword
          })
          .then(res => {
            console.log('密码已修改')
          })
          .catch(err => {
            console.log('err:', err)
          })
        alert('密码修改成功')
      } else {
        // 提示两次密码不一致
        console.log('两次密码输入不一致')
        alert('输入的两次密码不一致')
      }
    },
    confirmDelete () {
      const confirmResult = confirm('是否确认注销该账号')
      if (confirmResult) {
        // 执行注销账号逻辑
        axios
          .put('http://127.0.0.1:8000/api/users', {
            originalname: localStorage.getItem('nickname'),
            nickname: '该账号已注销',
            password: 'nullnull',
            email: 'null@qq.com',
            bio: '',
            permission: 'user',
            avatar: null,
            cancellation: true
          })
          .then(res => {
            alert('该账号已成功注销')
            this.$router.push({ name: 'login' })
          })
          .catch(err => {
            console.log('err:', err)
          })
        console.log('账号已注销')
        // Add your code here to perform the account deletion
      }
    }
  }
}
</script>

<style>
.small-input {
  width: 300px; /* 根据需要设置宽度 */
}

.delete-account-section {
  margin-top: 20px;
}

.delete-account-section h2 {
  font-size: 24px;
  margin-bottom: 10px;
}

</style>
