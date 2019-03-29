local xtrace=$(set +o | grep xtrace)
local error_on_clone=${ERROR_ON_CLONE}
if [ "$VERBOSE" == 'True' ]; then
    # enabling verbosity on whole plugin - default behavior
    set -o xtrace
fi

function configure_nova_rsd {
    # set neutron configs
    iniset $NEUTRON_CONF quotas quota_network -1
    iniset $NEUTRON_CONF quotas quota_subnet -1
    iniset $NEUTRON_CONF quotas quota_port -1
    iniset $NEUTRON_CONF quotas quota_security_group -1
    iniset $NEUTRON_CONF quotas quota_security_group_rule -1

    # set nova configs
    iniset $NOVA_CONF DEFAULT compute_driver "rsd.driver.RSDDriver"
    iniset $NOVA_CONF DEFAULT cpu_allocation_ratio 1.0
    iniset $NOVA_CONF DEFAULT ram_allocation_ratio 1.0
    # Disable arbitrary limits
    iniset $NOVA_CONF DEFAULT quota_instances -1
    iniset $NOVA_CONF DEFAULT quota_cores -1
    iniset $NOVA_CONF DEFAULT quota_ram -1
    iniset $NOVA_CONF DEFAULT quota_floating_ips -1
    iniset $NOVA_CONF DEFAULT quota_fixed_ips -1
    iniset $NOVA_CONF DEFAULT quota_metadata_items -1
    iniset $NOVA_CONF DEFAULT quota_injected_files -1
    iniset $NOVA_CONF DEFAULT quota_injected_file_path_length -1
    iniset $NOVA_CONF DEFAULT quota_security_groups -1
    iniset $NOVA_CONF DEFAULT quota_security_group_rules -1
    iniset $NOVA_CONF DEFAULT quota_key_pairs -1
    iniset $NOVA_CONF filter_scheduler enabled_filters "RetryFilter,AvailabilityZoneFilter,ComputeFilter,ComputeCapabilitiesFilter,ImagePropertiesFilter,CoreFilter,RamFilter,DiskFilter"

    iniset $NOVA_CONF rsd podm_ip ${PODM_IP}
    iniset $NOVA_CONF rsd podm_user ${PODM_USER}
    iniset $NOVA_CONF rsd podm_password ${PODM_PASSWD}
    iniset $NOVA_CONF rsd podm_port ${PODM_PORT}
    iniset $NOVA_CONF rsd auth_password ${OS_PASSWORD}
    iniset $NOVA_CONF rsd auth_url ${OS_AUTH_URL}
    iniset $NOVA_CONF rsd identity_version ${OS_IDENTITY_API_VERSION}
    iniset $NOVA_CONF rsd tenant_name ${OS_TENANT_NAME}
    iniset $NOVA_CONF rsd username ${OS_USERNAME}
}

# disabling ERROR_NO_CLONE to allow this plugin work with devstack-gate
ERROR_ON_CLONE=False

    case $1 in
        "stack")
            case $2 in
                "pre-install")
                    # cloning source code
                    echo_summary "Cloning of src files for rsd-virt-for-nova not required"
     #               sudo pip install -e "git+https://github.com/openstack/rsd-lib@517275b24fc86ce67a345b3aae2d4fa8564d18c1#egg=rsd_lib"
                ;;
                "install")
                    sudo pip install -e "${NOVA_RSD_DIR}"
                ;;
                "post-config")
                    configure_nova_rsd
                ;;
                "extra")
                    :
                ;;
            esac
        ;;
        "unstack")
             sudo pip uninstall "${NOVA_RSD_DIR}"
        ;;
        "clean")
            # Remove state and transient data
            # Remember clean.sh first calls unstack.sh
            # this is a noop
            :
        ;;
esac

ERROR_ON_CLONE=$error_on_clone
$xtrace
