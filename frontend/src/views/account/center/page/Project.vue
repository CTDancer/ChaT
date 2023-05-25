<template>
  <div>
    <a-card :bordered="false" class="scrollable-card">
      <a-list
        :item-layout="'horizontal'"
        :pagination="false"
        :loading="loading">
        <a-a-list-item v-for="user in users" :key="user.id" class="list-item">
          <a-a-list-item-meta description="">
            <a-avatar slot="avatar" size="large" shape="circle" :src="user.avatar" />
            <a slot="title" class="nickname">{{ user.nickname }}</a>
            <a-button slot="actions" class="button" @click="actions(user)">{{ user.permission === 'superuser' ? '降职' : '升职' }}</a-button>
          </a-a-list-item-meta>
          <div>
            <p ref="content"> </p>
          </div>
        </a-a-list-item>
      </a-list>
    </a-card>
  </div>
</template>

<script>
import { axios } from '@/utils/request'

export default {
  name: 'Project',
  data () {
    return {
      data: [],
      loading: true,
      users: []
    }
  },
  mounted () {
    this.getList()
    this.fetchUsers()
  },
  methods: {
    handleChange (value) {
      console.log(`selected ${value}`)
    },
    getList () {
      this.$http.get('/list/article', { params: { count: 100 } }).then(res => {
        console.log('res', res)
        this.data = res.result
        this.loading = false
      })
    },
    fetchUsers () {
      axios.get('http://127.0.0.1:8000/api/users', { params: { all: true } })
        .then(res => {
          this.users = res.users
          console.log('fetch users pass')
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    actions (user) {
      console.log('user: ', user)
      if (user.permission === 'user') {
        user.permission = 'superuser'
      } else {
        user.permission = 'user'
      }
      console.log(user.nickname)
      axios.put('http://127.0.0.1:8000/api/users', { nickname: user.nickname, permission: user.permission })
        .then(res => {
          console.log('res:', res)
          // this.fetchUsers()
        })
        .catch(err => {
          console.log('err:', err)
        })
    }
  }
}
</script>

<style lang="less" scoped>

.nickname {
  margin-left: 10px;
  font-size: large;
}

.button {
  float: right;
}

.list-item {
  margin-bottom: 10px;
}

</style>
