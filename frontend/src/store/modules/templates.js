import axios from 'axios'
import router from '@/router'
import { DesktopUtils } from '@/utils/desktopsUtils'
import { apiV3Segment } from '../../shared/constants'

export default {
  state: {
    templates: [],
    templates_loaded: false
  },
  getters: {
    getTemplates: state => {
      return state.templates
    },
    getTemplatesLoaded: state => {
      return state.templates_loaded
    }
  },
  mutations: {
    setTemplates: (state, templates) => {
      state.templates = templates
      state.templates_loaded = true
    }
  },
  actions: {
    fetchTemplates ({ commit }) {
      return new Promise((resolve, reject) => {
        axios.get(`${apiV3Segment}/user/templates`).then(response => {
          commit('setTemplates', DesktopUtils.parseTemplates(response.data))
          resolve()
        }).catch(e => {
          console.log(e)
          if (e.response.status === 503) {
            reject(e)
            router.push({ name: 'Maintenance' })
          } else if (e.response.status === 401 || e.response.status === 403) {
            this._vm.$snotify.clear()
            reject(e)
            router.push({ name: 'ExpiredSession' })
          } else {
            reject(e.response)
          }
        })
      })
    }
  }
}
